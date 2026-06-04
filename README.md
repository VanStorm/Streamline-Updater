# Streamline-Updater

Keeps the NVIDIA Streamline DLLs (`sl.*.dll`) in your games up to date. It scans your Steam, Epic, and GOG libraries, finds games that ship Streamline, and swaps in the newest DLLs from NVIDIA's official [Streamline SDK](https://github.com/NVIDIA-RTX/Streamline/) releases.

Useful if you want the latest DLSS / Reflex / Frame Generation runtime across your library without manually copying DLLs into every game folder.

## How it works

1. Grabs the latest SDK release straight from NVIDIA's GitHub.
2. Looks through your installed games for existing Streamline DLLs.
3. Compares what's installed against the SDK version.
4. Replaces anything older, and leaves newer or matching files alone.

If a game ships a newer DLL than the SDK, it gets left alone. Every file it touches gets backed up to a `.bak` first, so you can always roll back.

## Notes

- Reads the actual file version off each DLL. If a DLL has no version info, it falls back to comparing SHA-256 hashes so it doesn't reinstall identical files.
- The SDK download is checked after extraction. If it came down corrupt or incomplete, it wipes and re-downloads once before giving up.
- Run it in test mode first (option 1 in the menu) to see exactly what would change without touching a single file.
- Locked files (game running, DLL in use) are skipped with a warning instead of crashing the run.

## Requirements

- Windows
- Python 3.x

Install the dependencies with:

```bash
pip install -r requirements.txt
```

## Running it

Grab `Streamline-Updater.exe` from the release and double-click it, or run from source:

```bash
python updater.py
```

Pick test mode or live mode when prompted, choose which games to update, and confirm.

### Flags

- `--force` updates every matched DLL regardless of version, including downgrades. Use it when you want to pin everything to the current SDK.
- `--no-pause` skips the "Press Enter to exit" prompt on the EXE, handy for scripting.
