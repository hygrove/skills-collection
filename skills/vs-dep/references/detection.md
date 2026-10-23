# Tech-Stack Detection Matrix

This reference drives Step 1 of the skill. Scan the project root for markers,
then pick the matching start command. Substitute the values into the asset
templates.

## Frontend detection

Marker: `package.json` exists at project root (or a `frontend/` subfolder).

| Signal in package.json / files | Framework | Dev command | Default dev port | Notes |
|---|---|---|---|---|
| dep `vite` present | Vite | `npm run dev` (or `yarn`/`pnpm`) | read `vite.config.{ts,js}` `server.port`, else **5173** | also read `server.proxy` to get backend target port |
| dep `react-scripts` | CRA | `npm start` | **3000** | |
| dep `next` | Next.js | `npm run dev` | **3000** | framework handles its own proxy |
| no package.json, has `index.html` + bundler config | static/Vite | `npm run dev` | config-dependent | |

Frontend directory (`{{FRONTEND_DIR}}`): the folder containing `package.json`.
Often `frontend/` or project root.

Frontend build command (`{{FRONTEND_BUILD_CMD}}`): usually `npm run build`;
output lands in `dist/` (Vite) or `build/` (CRA). Adjust the prod script's
static path if not `dist/`.

Frontend dev command (`{{FRONTEND_CMD}}` in dev.ps1): `cmd /c npm run dev`
(or `yarn dev` / `pnpm dev` per lockfile present: `yarn.lock` -> yarn,
`pnpm-lock.yaml` -> pnpm).

## Backend detection

### Python (marker: `requirements.txt` or `pyproject.toml`)

| Signal | Framework | Start command (`{{BACKEND_ARGS}}` for uvicorn path) | Default port |
|---|---|---|---|
| dep `fastapi` (+`uvicorn`) | FastAPI | `python -m uvicorn <module>:app --app-dir "<root>" --host 127.0.0.1 --port <P>` | 8000 |
| dep `flask` | Flask | `python -m flask --app <module> run --host 127.0.0.1 --port <P>` | 5000 |
| dep `django` | Django | `python manage.py runserver 127.0.0.1:<P>` | 8000 |

- `{{BACKEND_EXE}}`: prefer `.venv/Scripts/python.exe` (Windows) or
  `venv/bin/python` (Linux/macOS) if that venv dir exists; else `python`/`python3`.
- `<module>:app` for FastAPI: find the file declaring `app = FastAPI()`
  (commonly `main.py`, `app.py`, or `backend/app/main.py` -> `backend.app.main:app`).
  When using `--app-dir "<root>"`, the module path is relative to root.
- Production (`{{PROD_BACKEND_ARGS}}`): drop `--reload`, add `--workers 4`
  (uvicorn) and bind `0.0.0.0` for LAN/external or keep `127.0.0.1` for local;
  for Flask/Django prefer `gunicorn` in prod.

### Node (marker: `package.json` with `express`/`fastify`/`nestjs`/`@nestjs/core`)
- `{{BACKEND_EXE}}`: `node`; `{{BACKEND_ARGS}}`: `<entry>.js` (e.g. `server.js`)
  or use `npm run dev`/`npm run start` via `cmd /c`. Default port **3000**,
  or read from code/`PORT` env.
- Production: `npm run build && npm run start` (or `pm2 start`).

### Go (marker: `go.mod`)
- `{{BACKEND_EXE}}`: `go`; `{{BACKEND_ARGS}}`: `run ./...` (dev) or build then run
  binary (prod). Default port **8080**.

### Rust (marker: `Cargo.toml`)
- `{{BACKEND_EXE}}`: `cargo`; `{{BACKEND_ARGS}}`: `run`. Default port **8080**.

### None / static only
- If no backend found, omit the backend task/template substitutions (leave a
  single-frontend dev.ps1 and tasks.json). If no frontend found, omit frontend.

## VS Code tasks.json substitution fragments

For `assets/tasks.json.template`, replace these placeholders:

- `{{BACKEND_CMD}}`: the backend exe path string, e.g. `.venv\\Scripts\\python.exe`.
- `{{BACKEND_ARGS}}`: a JSON array literal (no outer quotes), e.g.
  `["-m","uvicorn","backend.app.main:app","--app-dir","${workspaceFolder}","--host","127.0.0.1","--port","8000"]`.
- `{{BACKEND_PROBLEM_MATCHER}}`: a JSON object literal (no outer quotes) that
  matches the backend "listening" line. For uvicorn:
  `{"pattern":[{"regexp":"Uvicorn running on (http://[0-9a-zA-Z.:/\\[\\]]+)","message":1}],"background":{"activeOnStart":true,"beginsPattern":"Uvicorn running on","endsPattern":"Application startup complete"}}`.
- `{{FRONTEND_DIR}}`: e.g. `frontend`.
- `{{BACKEND_PORT}}` / `{{FRONTEND_PORT}}`: numeric strings.

## Service name
`{{SERVICE_NAME}}`: derive from the project folder name (PascalCase or keep
as-is). Used only for human-readable labels and terminal titles.
