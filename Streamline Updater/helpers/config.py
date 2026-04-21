from pathlib import Path
import sys

if getattr(sys, 'frozen', False):
    # Running as PyInstaller EXE
    ROOT_DIR = Path(sys.executable).resolve().parent
else:
    # Running as normal Python script
    ROOT_DIR = Path(__file__).resolve().parent.parent

SDK_DIR = ROOT_DIR / "streamline-sdk"
CACHE_FILE = ROOT_DIR / "cache.json"
LOG_FILE = ROOT_DIR / "logs.txt"

GITHUB_API_LATEST = "https://api.github.com/repos/NVIDIA-RTX/Streamline/releases/latest"

FORCE_UPDATE = False
