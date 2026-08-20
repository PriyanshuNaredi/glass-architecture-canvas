import io

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Any

from pipeline import run_pipeline

app = FastAPI(title="Glass — Generative Architecture Canvas")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GraphPayload(BaseModel):
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]


@app.get("/")
def health():
    return {"status": "glass-is-alive"}


@app.post("/generate")
def generate(payload: GraphPayload):
    result = run_pipeline(payload.nodes, payload.edges)

    errors = result.get("validation_errors", [])
    if errors:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid architecture graph", "details": errors},
        )

    zip_bytes = result.get("zip_buffer", b"")
    if not zip_bytes:
        return JSONResponse(
            status_code=500,
            content={"error": "Generation produced no output", "details": []},
        )

    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="glass-backend.zip"'},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
