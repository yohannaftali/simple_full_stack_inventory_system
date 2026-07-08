# Dev-only helper: reset local state so the app behaves like a fresh install.
#
# Clears:
#   - All __pycache__ dirs under src/ (compiled bytecode from before
#     sys.dont_write_bytecode was added, or from other tools/tests)
#   - storage/data and storage/temp (Flet's local app-storage dirs used by
#     `flet run` in desktop/dev mode - this is where SharedPreferences-backed
#     persisted values such as server url, login cookies/token, theme mode
#     would live), so the next run starts with nothing persisted, same as a
#     brand new install on a device.
#
# Does NOT touch .venv or build/ (use `uv sync` / rebuild the APK separately
# if you need to reset those too).
#
# Usage:
#   .\dev_reset.ps1          # clears pycache + storage
#   .\dev_reset.ps1 -WhatIf  # preview what would be removed, without deleting

param(
  [switch]$WhatIf
)

function Remove-PathContents {
  param([string]$Path, [string]$Label)

  if (-not (Test-Path $Path)) {
    Write-Host "  (skip) $Label not found: $Path" -ForegroundColor DarkGray
    return
  }

  $items = Get-ChildItem -Path $Path -Force -ErrorAction SilentlyContinue
  if (-not $items) {
    Write-Host "  (empty) $Label" -ForegroundColor DarkGray
    return
  }

  foreach ($item in $items) {
    if ($WhatIf) {
      Write-Host "  Would remove: $($item.FullName)" -ForegroundColor Yellow
    } else {
      Remove-Item -LiteralPath $item.FullName -Recurse -Force -Confirm:$false -ErrorAction SilentlyContinue
    }
  }
  if (-not $WhatIf) {
    Write-Host "  Cleared $Label" -ForegroundColor Green
  }
}

Write-Host "`nDev reset: clearing Python cache + app storage" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

Write-Host "`n[1/2] Removing __pycache__ directories under src/ ..." -ForegroundColor Yellow
$srcDir = Join-Path $PSScriptRoot "src"
$pycacheDirs = Get-ChildItem -Path $srcDir -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue
if (-not $pycacheDirs) {
  Write-Host "  No __pycache__ directories found." -ForegroundColor DarkGray
} else {
  foreach ($dir in $pycacheDirs) {
    if ($WhatIf) {
      Write-Host "  Would remove: $($dir.FullName)" -ForegroundColor Yellow
    } else {
      Remove-Item -LiteralPath $dir.FullName -Recurse -Force -Confirm:$false -ErrorAction SilentlyContinue
    }
  }
  if (-not $WhatIf) {
    Write-Host "  Removed $($pycacheDirs.Count) __pycache__ director$(if ($pycacheDirs.Count -eq 1) {'y'} else {'ies'})." -ForegroundColor Green
  }
}

Write-Host "`n[2/2] Clearing app storage (storage/data, storage/temp) ..." -ForegroundColor Yellow
Remove-PathContents -Path (Join-Path $PSScriptRoot "storage\data") -Label "storage/data"
Remove-PathContents -Path (Join-Path $PSScriptRoot "storage\temp") -Label "storage/temp"

if ($WhatIf) {
  Write-Host "`nDry run only - nothing was deleted. Re-run without -WhatIf to apply." -ForegroundColor Cyan
} else {
  Write-Host "`nDone. Next 'flet run' will behave like a fresh install (no persisted login/theme/server url)." -ForegroundColor Cyan
}
