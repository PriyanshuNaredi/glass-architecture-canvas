# Glass — The Generative Architecture Canvas

A node-based visual backend builder. Drag architecture components onto an infinite canvas, wire them together with glowing bezier curves, and hit **Generate Backend** to download a compiled FastAPI project as a `.zip`.

## Quick Start

### 1. Backend (FastAPI + LangGraph)

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8001
```

### 2. Frontend (React + React Flow + Tailwind)

```bash
cd frontend
npm install
npm run dev
```

Open the printed URL (default `http://localhost:5173`). The Vite dev server proxies `/generate` to the FastAPI backend on port 8001.

## Usage

1. Drag **Database Table**, **API Endpoint**, or **Auth Provider** from the left sidebar onto the canvas.
2. Connect nodes by dragging from one handle dot to another.
3. Click the glowing **Generate Backend** button at the bottom.
4. A `glass-backend.zip` downloads containing `main.py`, `models.py`, `Dockerfile`, and `requirements.txt`.

## Architecture

```
frontend/                  React + TypeScript + Vite + Tailwind
├── src/
│   ├── App.tsx            Canvas, sidebar, drag-drop, generate flow
│   ├── components/
│   │   ├── DatabaseNode.tsx
│   │   ├── APIEndpointNode.tsx
│   │   └── AuthNode.tsx
│   ├── index.css          Glassmorphic styles, glowing grid, edges
│   └── main.tsx
├── vite.config.ts         Dev proxy → localhost:8001
└── tailwind.config.js

backend/                   FastAPI + LangGraph pipeline
├── main.py                POST /generate endpoint
├── pipeline.py            LangGraph state machine:
│                          validator → code_generator → packager
└── requirements.txt
```

## LangGraph Pipeline

| Node | Role |
|------|------|
| `validator` | Parses the React Flow JSON; every `apiEndpointNode` must be wired to a `databaseNode`. Failures short-circuit to a `400` with the specific errors. |
| `architect` | System-prompted LLM that decides the file structure (`main.py`, `models.py`, `database.py`, `auth.py`, `requirements.txt`, `Dockerfile`) via structured output. |
| `coder` | LLM chain that writes each planned file from the graph relationships. |
| `packager` | Writes `generated_files` into an in-memory zip via `io.BytesIO` + `zipfile`. |

## LLM Providers (Phase 2)

Set the provider and key in `backend/.env` (copy from `.env.example`):

```bash
GLASS_LLM_PROVIDER=gemini   # gemini (default, free) | openai | anthropic
GEMINI_API_KEY=...          # free key: https://aistudio.google.com/apikey
```

- **Gemini** is the default because it has a free tier (`gemini-2.0-flash`).
- With **no API key configured**, the Architect and Coder automatically fall back to deterministic templates, so the app stays fully runnable.
- Model names are overridable via `GLASS_GEMINI_MODEL`, `GLASS_OPENAI_MODEL`, `GLASS_ANTHROPIC_MODEL`.

## Notes

- No API keys required. The code generator uses deterministic templates.
- Port 8001 is used because 8000 was occupied on this machine. Adjust `vite.config.ts` and `main.py` together if you change it.
- The generated zip is a runnable FastAPI app: `pip install -r requirements.txt && uvicorn main:app`.
