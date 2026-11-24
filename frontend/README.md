# The Omniscience Bound frontend

A standalone React and Vite workspace for the local FastAPI backend. It includes agent chat with sources and tool references, research plans and evidence, PDF indexing and retrieval, and a console for discovered MCP tools.

## Run locally

Use Node.js 22 and the Python environment described in the [backend README](../README.md). Start FastAPI in a PowerShell terminal from the backend directory.

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal, also starting from the backend directory, run the frontend.

```powershell
cd frontend
npm ci
npm run dev
```

Open the local address Vite prints, normally [http://127.0.0.1:5173](http://127.0.0.1:5173). The status button in the top bar shows backend connectivity and Ollama model availability.

## Backend connection

The development and preview servers proxy `/api` and `/health` to `http://127.0.0.1:8000`. To use a different backend address, set `BACKEND_URL` in `frontend/.env.local` and restart Vite. Model, search, and MCP credentials belong in the backend environment.

Chat and research answers require the configured Ollama model. PDF indexing and retrieval also require the configured embedding model. The sample PDFs in `../rag_documents/` can be uploaded from **Knowledge base**.

Chat messages and research run references are saved in this browser. Reopened chats send their prior turns with the next message. Research execution details are kept by FastAPI for the lifetime of its process. Indexed PDFs use the backend's persistent document store.

## Production build

```powershell
npm run build
npm run preview
```

The build is written to `dist/`. When serving those files from another web server, forward `/api/*` and `/health` on the same origin to FastAPI. The bundled frontend includes its fonts and icons for offline use.
