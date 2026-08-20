# Glass Backend

FastAPI server that turns a React Flow graph into a downloadable backend zip, orchestrated by a LangGraph state machine.

## Run

```bash
pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8001
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |
| POST | `/generate` | Accepts `{nodes, edges}` JSON, returns a zip (or 400 with validation errors) |

## LangGraph Pipeline

```
START → validator → architect → coder → packager → END
              └──(errors)──→ END
```

- **validator** — every `apiEndpointNode` must be wired to a `databaseNode`; dangling edges and unknown types are rejected.
- **architect** — structured-output LLM call that plans the file list (`main.py`, `models.py`, `database.py`, `auth.py`, `requirements.txt`, `Dockerfile`).
- **coder** — one LLM call per planned file, using the full graph JSON as context.
- **packager** — writes `generated_files` into an in-memory zip (`io.BytesIO` + `zipfile`).

## LLM Providers

Copy `.env.example` to `.env`:

```bash
GLASS_LLM_PROVIDER=gemini   # gemini (default, free) | openai | anthropic
GEMINI_API_KEY=...          # free key: https://aistudio.google.com/apikey
```

With no key configured, architect and coder fall back to deterministic templates so the app always works.

## Files

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app, CORS, `/generate` route, zip streaming |
| `pipeline.py` | LangGraph state machine, LLM factory, template fallback |
| `requirements.txt` | Python dependencies |
| `.env.example` | Provider/key configuration template |
