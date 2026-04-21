# Streamline-Updater

A Python utility that scans installed games (Steam, Epic Games, GOG) for NVIDIA Streamline DLLs and updates them to the latest publicly available version.

---

## Overview

This tool automatically:

- Detects installed games across supported launchers
- Searches for Streamline DLLs (`sl.*.dll`)
- Compares installed versions against the latest SDK release
- Updates outdated DLLs while:
  - avoiding downgrades
  - backing up existing files
  - preserving compatibility

---

## Features

- Supports:
  - Steam
  - Epic Games
  - GOG
- Recursive detection of Streamline DLL locations
- Version-aware updates (prevents overwriting newer game-provided DLLs)
- SHA-256 fallback comparison if version info is unavailable
- Automatic SDK download from GitHub
- Self-healing SDK extraction (re-download on corruption)
- Safe deployment:
  - atomic replacement (`.tmp` → `.bak`)
- Dry-run mode for previewing changes
- Optional `--force` override

---

## Requirements

- Python 3.x
- Windows

### Python dependencies

```bash
pip install requests pywin32
```
---

## Usage

Run the script directly from the Streamline-Updater.exe or the command line via:
```bash
python updater.py
```
