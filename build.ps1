# build.ps1 (repo root)

$ErrorActionPreference = "Stop"

$exeName    = "Streamline-Updater"
$exePath    = "dist\$exeName.exe"
$scriptPath = "Streamline Updater\updater.py"

# Verify PyInstaller is available before doing anything destructive
if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Error "pyinstaller not found on PATH. Install it with 'pip install pyinstaller'."
    exit 1
}

Write-Host "=== Cleaning previous builds ==="

Remove-Item -Recurse -Force build -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue
Remove-Item -Force *.spec -ErrorAction SilentlyContinue

Write-Host "=== Building EXE ==="

pyinstaller --onefile --clean --name "$exeName" "$scriptPath" --hidden-import win32api

if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller failed with exit code $LASTEXITCODE."
    exit $LASTEXITCODE
}

if (-not (Test-Path $exePath)) {
    Write-Error "Build reported success but $exePath was not produced."
    exit 1
}

Write-Host "=== Preparing ZIP structure ==="

$zipRoot = "dist\Streamline-Updater"
New-Item -ItemType Directory -Force -Path $zipRoot | Out-Null

Copy-Item "$scriptPath" -Destination $zipRoot

Write-Host "=== Creating ZIP ==="

$zipPath = "dist\Streamline-Updater.zip"

if (Test-Path $zipPath) {
    Remove-Item $zipPath
}

Compress-Archive -Path "$zipRoot\*" -DestinationPath $zipPath

Write-Host "=== Cleaning build artifacts ==="

Remove-Item -Recurse -Force build -ErrorAction SilentlyContinue
Remove-Item -Force *.spec -ErrorAction SilentlyContinue

Write-Host "=== Done ==="
Write-Host "EXE: $exePath"
Write-Host "ZIP: $zipPath"
