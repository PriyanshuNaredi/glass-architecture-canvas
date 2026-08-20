# Glass Frontend

React + TypeScript + Vite + Tailwind canvas built on `@xyflow/react`.

## Run

```bash
npm install
npm run dev
```

The dev server proxies `/generate` to the FastAPI backend on `http://localhost:8001` (see `vite.config.ts`).

## Components

| File | Purpose |
|------|---------|
| `src/App.tsx` | React Flow instance, drag-and-drop sidebar, floating Generate button |
| `src/components/DatabaseNode.tsx` | Frosted glass card with table name input + dynamic typed columns |
| `src/components/APIEndpointNode.tsx` | HTTP method dropdown + route path input |
| `src/components/AuthNode.tsx` | Auth strategy card (JWT) |
| `src/index.css` | Glassmorphic styles, glowing dot grid, neon edges, glass inputs |

## Node Data Contract

Everything typed on the canvas lives in the node's `data` object and is exported in the POST payload:

```jsonc
// databaseNode
{ "tableName": "users", "engine": "postgres",
  "columns": [{ "name": "email", "type": "String" }] }

// apiEndpointNode
{ "method": "GET", "path": "/api/v1/users" }

// authNode
{ "strategy": "jwt", "provider": "self-hosted" }
```

Column types: `String`, `Integer`, `Boolean`, `UUID`.

## Styling Notes

- Canvas: `#121212` charcoal with glowing indigo dot-matrix grid
- Nodes: `backdrop-blur` + `bg-white/10` + subtle borders; cyan glow on focus
- Edges: animated neon cyan dashes, purple when selected
- Form controls inside nodes use `nodrag nopan` so typing doesn't move the canvas
