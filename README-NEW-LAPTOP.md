
# New Laptop Setup — Python + React (Windows)

This repo has both a Python backend and a React frontend. Follow these steps on your **new Windows laptop** to clean old artifacts and reinstall everything from scratch.

---

## 0) Prereqs to install (once)

- **Git for Windows** (so you can clone/pull/push)
- **Python 3.10+** (let the installer add Python to PATH)
- **Node.js** (use the version your project used last time; Node 18/20 works for most projects)
- (Optional) **Yarn** or **pnpm** if your repo uses them
- (If native Node modules fail to build) **Microsoft C++ Build Tools** — add the *Desktop development with C++* workload

> Tip: If you used `nvm-windows` previously, install it and pick the exact Node version with `nvm use <version>`.

---

## 1) Deep clean the repo

Open **PowerShell** in the repo root and run:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser  # (first time only)
.\cleanup.ps1
```

This removes `node_modules`, build folders (`dist`, `build`, `.next`, etc.), Python caches (`__pycache__`, `.venv`, etc.), and other junk — without touching your source code or `.env` files.

> If you also want to nuke lockfiles (`package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`) to fully refresh dependency resolution, open `cleanup.ps1` and uncomment those lines.

---

## 2) Fresh install (backend + frontend)

From the repo root:

```powershell
.\bootstrap.ps1
```

What it does:

- **Backend** (`/backend` by default)
  - Creates a fresh `.venv`
  - Installs from `requirements.txt` (or `requirements-dev.txt` / `pyproject.toml` if present)
  - If it’s Django, it runs `python manage.py migrate`

- **Frontend** (`/frontend` by default)
  - Detects the right package manager from lockfiles
  - Installs with `npm ci` / `yarn install --frozen-lockfile` / `pnpm install --frozen-lockfile`
  - Runs `npm run build` if a `build` script exists

> Different folder names? Run: `.\bootstrap.ps1 -Backend api,service -Frontend web,app`

---

## 3) Run locally

Examples:

```powershell
# Backend — Django
cd backend
.\.venv\Scripts\Activate.ps1
python manage.py runserver

# Backend — FastAPI
cd backend
.\.venv\Scripts\Activate.ps1
pip install uvicorn  # if not already installed
uvicorn main:app --reload

# Frontend — Vite/React/Next
cd frontend
npm run dev
```

---

## 4) Environment variables / secrets

- Copy your `.env` files from the old laptop if they’re not in git.
- If you used Windows Credential Manager or keychain‑like tools, re‑create those entries.

---

## 5) Common pitfalls on a new Windows setup

- **node-gyp build errors** → Install Python (in PATH) and the **C++ Build Tools** workload.
- **Mismatched Node version** → Use `nvm-windows` to match the original Node version used by the project.
- **Pip compile issues** → Upgrade pip: `python -m pip install --upgrade pip`.
- **SSL / corporate proxy** → Set `npm config set proxy`/`https-proxy` and `pip.ini` accordingly.

---

## 6) Optional quality-of-life

- Install `ruff`/`black`/`prettier` and add a pre-commit hook.
- Add `.editorconfig` so editors agree on indentation/line endings.
- Consider `uv` (by Astral) for super-fast Python installs and `pnpm` for faster Node installs.

---

## 7) CI note

If you have a CI (GitHub Actions/GitLab), mirror the steps used there for consistent dev parity.

---

Happy hacking!
