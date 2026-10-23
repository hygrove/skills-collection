---
name: vs-dep
description: This skill should be used when a user wants to bootstrap dev/prod launch configuration for a software project. It auto-detects the tech stack (frontend framework like Vite/React/Next, backend framework/language like FastAPI/Flask/Django/Express/Go) and generates (1) an idempotent dev.ps1 launcher with port checks, (2) VS Code .vscode/tasks.json with folderOpen auto-start plus a terminal profile in .vscode/settings.json, and (3) a production start-prod.ps1 that builds the frontend and runs the backend in multi-worker prod mode. Triggers include "set up dev server auto-start", "generate dev.ps1 and .vscode config", "auto-start my frontend and backend", "create a production launch script", "configure folder-open auto run services".
agent_created: true
---

# Project Dev Launcher

## Overview
Generate run-ready launch configuration for any full-stack (or single-stack)
project with zero manual wiring. The skill detects the frontend and backend
tech stack from project markers, then emits an idempotent `dev.ps1`, VS Code
task/terminal profiles for "open folder -> services auto-start", and a
`start-prod.ps1` production launcher.

## When to Use
- User asks to auto-start dev services when a project opens or when a terminal opens.
- User wants a `dev.ps1` / `start-prod.ps1` without hand-writing it.
- User wants VS Code to launch the frontend and backend together (folderOpen / profile).
- Bootstrapping a new project's local dev/prod workflow.

## Workflow

### Step 1 - Detect the tech stack
Read `references/detection.md` and scan the target project root:
- Frontend: locate `package.json`; identify framework (Vite / CRA / Next) and the
  dev port (from `vite.config.*` `server.port`, or framework default). Read
  `server.proxy` to learn the backend target port.
- Backend: detect language/framework from `requirements.txt` / `pyproject.toml`
  (FastAPI / Flask / Django), `package.json` (Express / Nest), `go.mod`,
  `Cargo.toml`, or `manage.py`. Find the entry module and the correct start command.
- Virtual env: prefer `.venv/Scripts/python.exe` (Windows) or `venv/bin/python`
  (Linux/macOS) when present; fall back to `python` / `python3`.
Record: backend exe + args, backend port, frontend dir, frontend dev cmd + port,
frontend build cmd, service name.

### Step 2 - Generate dev.ps1 (dev mode)
Copy `assets/dev.ps1.template` to `<project>/scripts/dev.ps1` and substitute the
placeholders (`{{SERVICE_NAME}}`, `{{BACKEND_EXE}}`, `{{BACKEND_ARGS}}`,
`{{FRONTEND_DIR}}`, `{{FRONTEND_CMD}}`, `{{BACKEND_PORT}}`, `{{FRONTEND_PORT}}`).
Keep the script pure ASCII (PowerShell 5.1 reads .ps1 as ANSI without BOM - any
non-ASCII text corrupts). Preserve the `Test-PortListening` idempotency guard so
re-runs and the folderOpen + terminal-profile paths never double-bind a port.

### Step 3 - Generate .vscode/tasks.json
Copy `assets/tasks.json.template` to `<project>/.vscode/tasks.json`, substituting
`{{SERVICE_NAME}}`, `{{BACKEND_CMD}}`, `{{BACKEND_ARGS}}`,
`{{BACKEND_PROBLEM_MATCHER}}`, `{{FRONTEND_DIR}}`, `{{BACKEND_PORT}}`,
`{{FRONTEND_PORT}}`. Keep `"runOn": "folderOpen"` so services auto-start on folder
open. The `Stop` task kills whatever listens on the backend port.

### Step 4 - Generate .vscode/settings.json
Copy `assets/settings.json.template` to `<project>/.vscode/settings.json`,
substituting `{{SERVICE_NAME}}`. This defines a terminal profile that runs
`scripts/dev.ps1`. Leave `defaultProfile` OFF by default (avoid surprising the
user); tell them the one-line toggle to enable "terminal-open auto-start".

### Step 5 - Generate start-prod.ps1 (production mode)
Copy `assets/start-prod.ps1.template` to `<project>/scripts/start-prod.ps1`,
substituting the prod backend args (`--workers N`, no `--reload`, bind
`0.0.0.0` or `127.0.0.1`), the build cmd, ports, and dirs. The script builds the
frontend then launches the backend in production mode.

### Step 6 - Validate
- PowerShell syntax:
  `powershell -NoProfile -ExecutionPolicy RemoteSigned -Command "$e=$null; [System.Management.Automation.Language.Parser]::ParseFile('<file>',[ref]$null,[ref]$e); if($e){exit 1}else{'OK'}"`
- JSON: `node -e "JSON.parse(require('fs').readFileSync('<file>','utf8'))"`
Report the generated file list and how to enable terminal-auto-start.

## Notes
- Idempotency: always guard service starts with a port-listen check so re-runs
  and folderOpen + profile never double-bind a port.
- PowerShell 5.1 encoding: ship pure-ASCII .ps1; never rely on UTF-8-without-BOM
  for Chinese/emoji inside scripts.
- Cross-platform: on non-Windows, emit `.sh` equivalents instead of `.ps1`
  (detect `$env:OS` / `$IsWindows`).
- `.vscode/` is often git-ignored; remind the user if they want team sharing.

## Resources
- `references/detection.md` - tech-stack detection matrix and per-stack commands.
- `assets/dev.ps1.template` - dev launcher template (ASCII, idempotent).
- `assets/start-prod.ps1.template` - production launcher template.
- `assets/tasks.json.template` - VS Code tasks template (folderOpen).
- `assets/settings.json.template` - VS Code terminal profile template.
