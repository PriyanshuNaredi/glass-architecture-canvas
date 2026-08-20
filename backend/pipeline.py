import io
import json
import os
import re
import zipfile
from typing import Any, Literal, Optional

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

load_dotenv()


# ─── State ────────────────────────────────────────────────────────────────────

class PipelineState(TypedDict, total=False):
    raw_json: dict[str, Any]
    validation_errors: list[str]
    file_plan: list[dict[str, str]]
    generated_files: dict[str, str]
    zip_buffer: bytes
    provider_used: str


# ─── LLM factory: Gemini (free, default) → OpenAI → Anthropic ────────────────

def get_llm(temperature: float = 0.2):
    """Return a chat model based on GLASS_LLM_PROVIDER (default: gemini).

    Returns None when the selected provider has no API key configured,
    which downstream agents treat as a signal to use template fallback.
    """
    provider = os.getenv("GLASS_LLM_PROVIDER", "gemini").lower()

    if provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return None
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=os.getenv("GLASS_GEMINI_MODEL", "gemini-2.0-flash"),
            google_api_key=api_key,
            temperature=temperature,
        )

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=os.getenv("GLASS_OPENAI_MODEL", "gpt-4o-mini"),
            api_key=api_key,
            temperature=temperature,
        )

    if provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return None
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=os.getenv("GLASS_ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
            api_key=api_key,
            temperature=temperature,
        )

    return None


# ─── Node 1: Validator ────────────────────────────────────────────────────────

def validator(state: PipelineState) -> dict:
    raw = state.get("raw_json", {})
    nodes = raw.get("nodes", [])
    edges = raw.get("edges", [])
    errors: list[str] = []

    if not nodes:
        return {"validation_errors": ["Canvas is empty. Add at least one node before generating."]}

    node_ids = {n.get("id") for n in nodes}
    node_type_by_id = {n.get("id"): n.get("type", "") for n in nodes}

    for node in nodes:
        if node.get("type") not in ("databaseNode", "apiEndpointNode", "authNode"):
            errors.append(f"Node '{node.get('id')}' has unknown type '{node.get('type')}'.")

    for edge in edges:
        if edge.get("source") not in node_ids:
            errors.append(f"Edge '{edge.get('id')}' references missing source node '{edge.get('source')}'.")
        if edge.get("target") not in node_ids:
            errors.append(f"Edge '{edge.get('id')}' references missing target node '{edge.get('target')}'.")

    # Every API endpoint must be wired to at least one database (either direction).
    for node in nodes:
        if node.get("type") != "apiEndpointNode":
            continue
        nid = node.get("id")
        path = node.get("data", {}).get("path", nid)
        connected_to_db = any(
            (
                (e.get("source") == nid and node_type_by_id.get(e.get("target")) == "databaseNode")
                or (e.get("target") == nid and node_type_by_id.get(e.get("source")) == "databaseNode")
            )
            for e in edges
        )
        if not connected_to_db:
            errors.append(
                f"Endpoint '{path}' is not connected to any Database node. "
                f"Draw a wire between the endpoint and a database table."
            )

    return {"validation_errors": errors}


def route_after_validation(state: PipelineState) -> Literal["architect", "__end__"]:
    return "architect" if not state.get("validation_errors") else END


# ─── Node 2: Architect (LLM decides the file structure) ──────────────────────

class FilePlan(BaseModel):
    files: list[dict[str, str]] = Field(
        description="Ordered list of files to generate; each has 'filename' and 'purpose'."
    )


ARCHITECT_SYSTEM_PROMPT = """You are the Architect agent inside Glass, a visual backend builder.
You receive a validated React Flow graph (nodes: databaseNode, apiEndpointNode, authNode; edges are wires).
Decide the minimal, clean file structure for a FastAPI backend that implements this graph.

Rules:
- Always include: main.py, models.py, requirements.txt, Dockerfile.
- Include database.py when at least one databaseNode exists.
- Include auth.py when at least one authNode exists.
- No other files unless strictly necessary. Never invent config for services not in the graph.

Respond ONLY with the structured file plan."""


def architect(state: PipelineState) -> dict:
    raw = state.get("raw_json", {})
    node_types = [n.get("type") for n in raw.get("nodes", [])]
    has_db = "databaseNode" in node_types
    has_auth = "authNode" in node_types

    default_plan = [
        {"filename": "main.py", "purpose": "FastAPI app entrypoint with all routes wired"},
        {"filename": "models.py", "purpose": "Pydantic models for each database table"},
    ]
    if has_db:
        default_plan.append({"filename": "database.py", "purpose": "In-memory data stores and CRUD helpers"})
    if has_auth:
        default_plan.append({"filename": "auth.py", "purpose": "JWT auth dependency and token helpers"})
    default_plan += [
        {"filename": "requirements.txt", "purpose": "Python dependencies"},
        {"filename": "Dockerfile", "purpose": "Container image running uvicorn"},
    ]

    llm = get_llm(temperature=0.1)
    if llm is None:
        return {"file_plan": default_plan, "provider_used": "template-fallback"}

    try:
        structured = llm.with_structured_output(FilePlan)
        result = structured.invoke([
            SystemMessage(content=ARCHITECT_SYSTEM_PROMPT),
            HumanMessage(content=f"Validated architecture graph:\n{json.dumps(raw, indent=2)}"),
        ])
        plan = [
            {"filename": f["filename"].strip().lstrip("/"), "purpose": f.get("purpose", "")}
            for f in result.files
            if f.get("filename")
        ]
        if not plan:
            raise ValueError("Architect returned an empty file plan")
        return {"file_plan": plan, "provider_used": os.getenv("GLASS_LLM_PROVIDER", "gemini")}
    except Exception:
        return {"file_plan": default_plan, "provider_used": "template-fallback"}


# ─── Node 3: Coder (LLM writes each file; templates as fallback) ─────────────

CODER_SYSTEM_PROMPT = """You are the Coder agent inside Glass, a visual backend builder.
You write ONE complete, runnable file at a time for a FastAPI backend derived from a React Flow graph.

Graph semantics:
- databaseNode.data.tableName → a Pydantic model + an in-memory list store named <table>_store.
- databaseNode.data.columns → typed fields on the model: String→str, Integer→int, Boolean→bool, UUID→str.
- apiEndpointNode.data.method/path → a FastAPI route. GET returns the store contents, POST appends a body dict, PUT/DELETE operate by id.
- authNode.data.strategy == "jwt" → protect routes with an OAuth2PasswordBearer dependency decoding HS256 JWTs.
- Wires (edges) define which endpoint reads/writes which table, and which auth guards which endpoint.

Rules:
- Output ONLY the raw file content. No markdown fences, no commentary.
- Complete files only — no placeholders, no TODOs, no ellipses.
- Python 3.12, FastAPI, pydantic v2. Keep it dependency-light."""


def _extract_code(text: str) -> str:
    """Strip markdown fences if the model wrapped its output anyway."""
    fence = re.search(r"```(?:\w+)?\n(.*?)```", text, re.DOTALL)
    return fence.group(1).strip() + "\n" if fence else text.strip() + "\n"


def coder(state: PipelineState) -> dict:
    raw = state.get("raw_json", {})
    plan = state.get("file_plan", [])
    provider = state.get("provider_used", "")

    if provider == "template-fallback":
        return {"generated_files": _template_generate(raw, plan)}

    llm = get_llm(temperature=0.2)
    if llm is None:
        return {"generated_files": _template_generate(raw, plan)}

    files: dict[str, str] = {}
    graph_json = json.dumps(raw, indent=2)
    for item in plan:
        filename = item["filename"]
        purpose = item.get("purpose", "")
        try:
            response = llm.invoke([
                SystemMessage(content=CODER_SYSTEM_PROMPT),
                HumanMessage(content=(
                    f"Architecture graph:\n{graph_json}\n\n"
                    f"Write the file `{filename}`.\nPurpose: {purpose}\n"
                    f"Other files in this project: {', '.join(i['filename'] for i in plan if i['filename'] != filename)}.\n"
                    f"Import between them as needed. Output only the file content."
                )),
            ])
            content = _extract_code(response.content if isinstance(response.content, str) else str(response.content))
            if content.strip():
                files[filename] = content
            else:
                files[filename] = _template_for(filename, raw)
        except Exception:
            files[filename] = _template_for(filename, raw)

    return {"generated_files": files}


# ─── Template fallback (keeps the app working with zero API keys) ────────────

def _template_generate(raw: dict, plan: list[dict[str, str]]) -> dict[str, str]:
    return {item["filename"]: _template_for(item["filename"], raw) for item in plan}


def _template_for(filename: str, raw: dict) -> str:
    nodes = raw.get("nodes", [])
    edges = raw.get("edges", [])
    databases = [n.get("data", {}) for n in nodes if n.get("type") == "databaseNode"]
    endpoints = [n.get("data", {}) for n in nodes if n.get("type") == "apiEndpointNode"]
    auth_nodes = [n.get("data", {}) for n in nodes if n.get("type") == "authNode"]
    has_jwt = any(a.get("strategy") == "jwt" for a in auth_nodes)

    if filename == "main.py":
        lines = [
            "from fastapi import FastAPI, HTTPException, Depends",
            "from fastapi.middleware.cors import CORSMiddleware",
            "from models import *",
            "",
        ]
        if databases:
            lines.append("from database import *")
        if has_jwt:
            lines.append("from auth import get_current_user")
        lines += [
            "",
            'app = FastAPI(title="Glass Generated Backend")',
            "",
            "app.add_middleware(",
            "    CORSMiddleware,",
            '    allow_origins=["*"],',
            "    allow_credentials=True,",
            '    allow_methods=["*"],',
            '    allow_headers=["*"],',
            ")",
            "",
        ]
        for ep in endpoints:
            method = (ep.get("method") or "GET").lower()
            path = ep.get("path") or "/items"
            if not path.startswith("/"):
                path = "/" + path
            func_name = f"{method}_{path.strip('/').replace('/', '_').replace('-', '_').replace('{', '').replace('}', '')}"
            lines.append(f'@app.{method}("{path}")')
            if has_jwt:
                lines.append(f"def {func_name}(user: str = Depends(get_current_user)):")
            else:
                lines.append(f"def {func_name}():")
            body = {
                "get": '    return {"status": "ok", "data": []}',
                "post": '    return {"status": "created"}',
                "put": '    return {"status": "updated"}',
                "delete": '    return {"status": "deleted"}',
            }.get(method, '    return {"status": "ok"}')
            lines.append(body)
            lines.append("")
        lines += [
            "",
            'if __name__ == "__main__":',
            "    import uvicorn",
            '    uvicorn.run(app, host="0.0.0.0", port=8000)',
            "",
        ]
        return "\n".join(lines)

    if filename == "models.py":
        type_map = {"String": "str", "Integer": "int", "Boolean": "bool", "UUID": "str"}
        lines = ["from pydantic import BaseModel", "from typing import Optional", ""]
        tables = databases or [{"tableName": "items", "columns": []}]
        for db in tables:
            class_name = (db.get("tableName") or "items").capitalize()
            lines.append(f"class {class_name}(BaseModel):")
            lines.append("    id: int")
            for col in db.get("columns", []):
                col_name = (col.get("name") or "").strip()
                if not col_name:
                    continue
                py_type = type_map.get(col.get("type", "String"), "str")
                lines.append(f"    {col_name}: Optional[{py_type}] = None")
            lines.append("    created_at: Optional[str] = None")
            lines.append("")
        return "\n".join(lines)

    if filename == "database.py":
        lines = ["# In-memory stores generated from the Glass canvas", ""]
        for db in databases or [{"tableName": "items"}]:
            table = db.get("tableName") or "items"
            lines += [f"{table}_store: list[dict] = []", ""]
        return "\n".join(lines)

    if filename == "auth.py":
        return "\n".join([
            "import jwt",
            "from fastapi import Depends, HTTPException",
            "from fastapi.security import OAuth2PasswordBearer",
            "",
            'SECRET_KEY = "change-me-in-production"',
            'ALGORITHM = "HS256"',
            "oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')",
            "",
            "",
            "def get_current_user(token: str = Depends(oauth2_scheme)) -> str:",
            "    try:",
            "        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])",
            '        user = payload.get("sub")',
            "        if user is None:",
            '            raise HTTPException(status_code=401, detail="Invalid token payload")',
            "        return user",
            "    except jwt.PyJWTError:",
            '        raise HTTPException(status_code=401, detail="Invalid token")',
            "",
        ])

    if filename == "requirements.txt":
        lines = ["fastapi>=0.115.0", "uvicorn[standard]>=0.30.6", "pydantic>=2.9.2"]
        if has_jwt:
            lines += ["PyJWT>=2.9.0"]
        return "\n".join(lines) + "\n"

    if filename == "Dockerfile":
        return "\n".join([
            "FROM python:3.12-slim",
            "",
            "WORKDIR /app",
            "",
            "COPY requirements.txt .",
            "RUN pip install --no-cache-dir -r requirements.txt",
            "",
            "COPY . .",
            "",
            "EXPOSE 8000",
            "",
            'CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]',
            "",
        ])

    return f"# Glass could not generate a template for {filename}\n"


# ─── Node 4: Packager (in-memory ZIP via io.BytesIO + zipfile) ───────────────

def packager(state: PipelineState) -> dict:
    files = state.get("generated_files", {})
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return {"zip_buffer": buffer.getvalue()}


# ─── Graph assembly ───────────────────────────────────────────────────────────

def build_pipeline():
    graph = StateGraph(PipelineState)
    graph.add_node("validator", validator)
    graph.add_node("architect", architect)
    graph.add_node("coder", coder)
    graph.add_node("packager", packager)

    graph.add_edge(START, "validator")
    graph.add_conditional_edges("validator", route_after_validation)
    graph.add_edge("architect", "coder")
    graph.add_edge("coder", "packager")
    graph.add_edge("packager", END)
    return graph.compile()


pipeline = build_pipeline()


def run_pipeline(nodes: list[dict], edges: list[dict]) -> PipelineState:
    return pipeline.invoke({
        "raw_json": {"nodes": nodes, "edges": edges},
        "validation_errors": [],
        "file_plan": [],
        "generated_files": {},
        "zip_buffer": b"",
        "provider_used": "",
    })
