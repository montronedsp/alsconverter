# Build a Windows GUI executable with PyInstaller (one-folder, faster start).
# Run from repo root:
#   python -m pip install -e ".[dev]" pyinstaller
#   powershell -File scripts/build-windows.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Py = $null
$cmd = Get-Command python -ErrorAction SilentlyContinue
if ($cmd) {
  $Py = $cmd.Source
} else {
  $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
  if ($pyLauncher) {
    $Py = (& $pyLauncher.Source -3 -c "import sys; print(sys.executable)").Trim()
  }
}
if (-not $Py -or -not (Test-Path $Py)) {
  throw "Python not found on PATH. Install Python 3 and ensure 'python' or 'py' is available."
}

& $Py -m pip install -e ".[dev]" pyinstaller -q

$dist = Join-Path $Root "dist\ALSConverter"
if (Test-Path $dist) { Remove-Item $dist -Recurse -Force }

& $Py -m PyInstaller `
  --noconfirm `
  --clean `
  --windowed `
  --name ALSConverter `
  --paths src `
  --collect-data alsdowngrade `
  --distpath dist `
  --workpath build\pyinstaller `
  src\alsdowngrade\gui.py

Write-Host ""
Write-Host "Built: $Root\dist\ALSConverter\ALSConverter.exe"
Write-Host "Zip the ALSConverter folder to distribute. No install required."
