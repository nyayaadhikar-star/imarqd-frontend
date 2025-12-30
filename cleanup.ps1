
<# 
  cleanup.ps1 — Deep clean a Python + React monorepo on Windows
  Usage:
    1) Right‑click → "Run with PowerShell" OR in a PS terminal:  .\cleanup.ps1
    2) If ExecutionPolicy blocks it, run as Admin once:  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
#>

param(
  [string]$Root = (Get-Location).Path
)

Write-Host "Starting deep clean in: $Root" -ForegroundColor Cyan

# Common folders to remove (recursive)
$folders = @(
  # Node/JS
  "node_modules", ".next", ".nuxt", "dist", "build", ".vite", ".parcel-cache", ".cache",
  ".turbo", "coverage", ".eslintcache", ".angular", ".svelte-kit", "storybook-static",
  # Python
  ".venv", "venv", "env", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
  "build", "dist", "*.egg-info", ".ipynb_checkpoints"
)

# Common files to remove
$files = @(
  # JS lock files (optional — uncomment the ones you want to remove)
  #"package-lock.json", 
  #"yarn.lock", 
  #"pnpm-lock.yaml",
  # Misc
  ".DS_Store", "Thumbs.db"
)

# Function to remove with safety
function Remove-Target {
  param([string]$PathItem)
  if (Test-Path -LiteralPath $PathItem) {
    try {
      # Use -Force for hidden/system files, -Recurse for dirs
      if ((Get-Item -LiteralPath $PathItem).PSIsContainer) {
        Remove-Item -LiteralPath $PathItem -Recurse -Force -ErrorAction Stop
        Write-Host "Removed directory: $PathItem" -ForegroundColor DarkGray
      } else {
        Remove-Item -LiteralPath $PathItem -Force -ErrorAction Stop
        Write-Host "Removed file: $PathItem" -ForegroundColor DarkGray
      }
    } catch {
      Write-Warning "Could not remove $PathItem. Error: $($_.Exception.Message)"
    }
  }
}

# Walk the repo removing targets
Get-ChildItem -LiteralPath $Root -Recurse -Force -ErrorAction SilentlyContinue | ForEach-Object {
  foreach ($f in $folders) {
    # wildcard match for egg-info, etc.
    if ($_ -is [System.IO.DirectoryInfo] -and $_.Name -like $f) {
      Remove-Target -PathItem $_.FullName
    }
  }
  foreach ($fi in $files) {
    if ($_ -is [System.IO.FileInfo] -and $_.Name -eq $fi) {
      Remove-Target -PathItem $_.FullName
    }
  }
}

Write-Host "Clean complete." -ForegroundColor Green
