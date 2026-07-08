# This script sets up a Python virtual environment using uv and installs dependencies
# for the Grid Martingale Lite Telegram bot.

Write-Host "Setting up Python virtual environment with uv..." -ForegroundColor Green

# Check if uv is installed
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  Write-Host "uv is not installed. Installing uv..." -ForegroundColor Yellow
  # Install uv using the official installer
  Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
  if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to install uv. Please install it manually and try again." -ForegroundColor Red
    exit 1
  }
}

# Check if Python is installed
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  Write-Host "Python is not installed. Please install Python and try again." -ForegroundColor Red
  exit 1
}

$venvPath = Join-Path $PSScriptRoot '.venv'
$pyCfg = Join-Path $venvPath 'pyvenv.cfg'

# If venv exists but is broken (missing pyvenv.cfg) try to remove and recreate it
if (Test-Path $venvPath -PathType Container) {
  if (-not (Test-Path $pyCfg)) {
    Write-Host "Found existing virtual environment but missing pyvenv.cfg — attempting to recreate..." -ForegroundColor Yellow
    try {
      Remove-Item -LiteralPath $venvPath -Recurse -Force -ErrorAction Stop
      Write-Host "Removed broken virtual environment." -ForegroundColor Green
    } catch {
      Write-Host "Failed to remove .venv — attempting to stop Python processes that may be locking files..." -ForegroundColor Yellow
      # Attempt to find python processes that may belong to the venv and stop them
      $pythonProcs = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
        try { $_.Path -and ($_.Path -like "*$venvPath*") } catch { $false }
      }
      if ($pythonProcs) {
        $pythonProcs | ForEach-Object { 
          try { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue } catch { }
        }
        Start-Sleep -Seconds 1
        try { Remove-Item -LiteralPath $venvPath -Recurse -Force -ErrorAction Stop; Write-Host "Removed broken virtual environment after stopping python processes." -ForegroundColor Green } catch {
          Write-Host "Still unable to remove .venv. Close any programs using the venv or remove it manually and re-run this script." -ForegroundColor Red
          exit 1
        }
      } else {
        Write-Host "No python processes found that appear to use the venv. Close programs that may be using files in .venv and try again." -ForegroundColor Red
        exit 1
      }
    }
  } else {
    Write-Host "Existing virtual environment looks healthy (pyvenv.cfg present)." -ForegroundColor Green
  }
}

# Sync dependencies using uv (this will create the venv if missing)
Write-Host "Installing dependencies with uv..." -ForegroundColor Yellow
uv sync
if ($LASTEXITCODE -ne 0) {
  Write-Host "Failed to install dependencies with uv." -ForegroundColor Red
  exit 1
}

# Try to activate the venv in the current session
$activatePath = Join-Path $venvPath 'Scripts\Activate.ps1'
if (Test-Path $activatePath) {
  try {
    . $activatePath
    Write-Host "Activated virtual environment: $venvPath" -ForegroundColor Green
  } catch {
    Write-Host "Failed to activate virtual environment automatically. You can activate it with:`n. $activatePath" -ForegroundColor Yellow
  }
} else {
  Write-Host "Activation script not found after uv sync. You can run commands with 'uv run <command>' or activate manually if the venv exists." -ForegroundColor Yellow
}
