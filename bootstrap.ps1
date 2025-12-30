
<# 
  bootstrap.ps1 - Fresh install for Python backend(s) + React frontend(s) on Windows
  Usage examples:
    .\bootstrap.ps1
    .\bootstrap.ps1 -Backend api -Frontend web
    .\bootstrap.ps1 -Backend api,service -Frontend web,app
#>

param(
  [string[]]$Backend = @("apps/api"),
  [string[]]$Frontend = @("apps/web"),
  [switch]$SkipNodeGypCheck
)

function Assert-Command($name) {
  $cmd = Get-Command $name -ErrorAction SilentlyContinue
  if (-not $cmd) {
    throw "Required command '$name' is not available in PATH."
  }
  return $true
}

function Detect-Python {
  $candidates = @("python", "py")
  foreach ($c in $candidates) {
    $cmd = Get-Command $c -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Name }
  }
  throw "Python not found. Install Python 3.10+ and ensure it's in PATH."
}

function Detect-Node {
  $cmd = Get-Command node -ErrorAction SilentlyContinue
  if (-not $cmd) { throw "Node.js not found. Install Node 18+ (or your project's version) and ensure it's in PATH." }
  return "node"
}

function Install-Backend($dir) {
  if (-not (Test-Path $dir)) {
    Write-Host "Skipping backend '$dir' (not found)..." -ForegroundColor Yellow
    return
  }
  Push-Location $dir
  try {
    Write-Host "== Backend: $dir ==" -ForegroundColor Cyan
    $py = Detect-Python

    if (-not (Test-Path ".\.venv")) {
      & $py -m venv .venv
      if ($LASTEXITCODE -ne 0) { throw "Failed to create venv in $dir" }
    }

    $venvActivate = ".\.venv\Scripts\Activate.ps1"
    if (Test-Path $venvActivate) {
      . $venvActivate
    } else {
      throw "Can't find venv activation script at $venvActivate"
    }

    python -m pip install --upgrade pip wheel setuptools

    if (Test-Path ".\requirements.txt") {
      pip install -r requirements.txt
    } elseif (Test-Path ".\requirements-dev.txt") {
      pip install -r requirements-dev.txt
    } elseif (Test-Path ".\pyproject.toml") {
      pip install .
    } else {
      Write-Host "No requirements.txt or pyproject.toml found in $dir - skipping pip install." -ForegroundColor Yellow
    }

    if (Test-Path ".\manage.py") {
      Write-Host "Running Django migrations (best-effort)..." -ForegroundColor DarkCyan
      python manage.py migrate
    } elseif (Test-Path ".\app.py" -or Test-Path ".\main.py") {
      Write-Host "Detected possible Flask/FastAPI. Start with: uvicorn main:app --reload (or your entrypoint)." -ForegroundColor DarkCyan
    }
  } finally {
    Pop-Location
  }
}

function Install-Frontend($dir) {
  if (-not (Test-Path $dir)) {
    Write-Host "Skipping frontend '$dir' (not found)..." -ForegroundColor Yellow
    return
  }
  Push-Location $dir
  try {
    Write-Host "== Frontend: $dir ==" -ForegroundColor Cyan
    Detect-Node | Out-Null

    if (-not $SkipNodeGypCheck) {
      Write-Host "Checking native build tools (node-gyp)..." -ForegroundColor DarkCyan
      $hasPython = (Get-Command python -ErrorAction SilentlyContinue) -ne $null
      $vsPath = "$Env:ProgramFiles(x86)\Microsoft Visual Studio\Installer"
      if (-not $hasPython) { Write-Host "Tip: node-gyp often requires Python in PATH." -ForegroundColor Yellow }
      if (-not (Test-Path $vsPath)) { Write-Host "Tip: If native builds fail, install 'Desktop development with C++' (Build Tools)." -ForegroundColor Yellow }
    }

    if (Test-Path "yarn.lock") {
      Write-Host "Detected Yarn lockfile -> yarn install --frozen-lockfile" -ForegroundColor DarkCyan
      Assert-Command yarn | Out-Null
      yarn install --frozen-lockfile
    } elseif (Test-Path "pnpm-lock.yaml") {
      Write-Host "Detected pnpm lockfile -> pnpm install --frozen-lockfile" -ForegroundColor DarkCyan
      Assert-Command pnpm | Out-Null
      pnpm install --frozen-lockfile
    } elseif (Test-Path "package-lock.json") {
      Write-Host "Detected npm lockfile -> npm ci" -ForegroundColor DarkCyan
      Assert-Command npm | Out-Null
      npm ci
    } else {
      Write-Host "No lockfile found -> npm install" -ForegroundColor DarkCyan
      Assert-Command npm | Out-Null
      npm install
    }

    if (Test-Path "package.json") {
      $pkg = Get-Content package.json | Out-String
      if ($pkg -match '"build"\s*:\s*') {
        Write-Host "Running frontend build..." -ForegroundColor DarkCyan
        npm run build
      } else {
        Write-Host "No build script found; skipping build." -ForegroundColor Yellow
      }
    }
  } finally {
    Pop-Location
  }
}

Write-Host "Bootstrapping workspace..." -ForegroundColor Cyan

try { Assert-Command git | Out-Null } catch { Write-Warning "Git not found in PATH. Install Git for Windows for the best experience." }

foreach ($b in $Backend)  { Install-Backend $b }
foreach ($f in $Frontend) { Install-Frontend $f }

Write-Host ""
Write-Host "All done! Next steps (examples):" -ForegroundColor Green
Write-Host "  - Start backend (Django):    cd backend; .\.venv\Scripts\Activate.ps1; python manage.py runserver" -ForegroundColor Gray
Write-Host "  - Start backend (FastAPI):   cd backend; .\.venv\Scripts\Activate.ps1; uvicorn main:app --reload" -ForegroundColor Gray
Write-Host "  - Start frontend dev:        cd frontend; npm run dev" -ForegroundColor Gray
