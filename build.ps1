# build.ps1 (repo root)

$ErrorActionPreference = "Stop"

$projectRoot = "Streamline Updater"
$exeName     = "Streamline-Updater"
$exePath     = "dist\$exeName.exe"

# Verify PyInstaller is available before doing anything destructive
if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Error "pyinstaller not found on PATH. Install it with 'pip install pyinstaller'."
    exit 1
}

Write-Host "=== Cleaning previous builds ==="

Remove-Item -Recurse -Force build -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force *.spec -ErrorAction SilentlyContinue

Write-Host "=== Building EXE ==="

pyinstaller --onefile --clean --name "$exeName" "$projectRoot\updater.py" --hidden-import win32api

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

# Copy updater.py
Copy-Item "$projectRoot\updater.py" -Destination $zipRoot

# Copy helpers (excluding __pycache__)
$helpersSource = "$projectRoot\helpers"
$helpersTarget = "$zipRoot\helpers"

New-Item -ItemType Directory -Force -Path $helpersTarget | Out-Null

Get-ChildItem -Path $helpersSource -Recurse | ForEach-Object {
    if ($_.FullName -notmatch "__pycache__") {
        $dest = $_.FullName.Replace(
            (Resolve-Path $helpersSource).Path,
            (Resolve-Path $helpersTarget).Path
        )

        if ($_.PSIsContainer) {
            New-Item -ItemType Directory -Force -Path $dest | Out-Null
        } else {
            Copy-Item $_.FullName -Destination $dest -Force
        }
    }
}

Write-Host "=== Creating ZIP ==="

$zipPath = "dist\Streamline-Updater.zip"

if (Test-Path $zipPath) {
    Remove-Item $zipPath
}

Compress-Archive -Path "$zipRoot\*" -DestinationPath $zipPath

Write-Host "=== Done ==="
Write-Host "EXE: $exePath"
Write-Host "ZIP: $zipPath"
