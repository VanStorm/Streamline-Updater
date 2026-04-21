from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

SDK_DIR = ROOT_DIR / "streamline-sdk"
CACHE_FILE = ROOT_DIR / "cache.json"
LOG_FILE = ROOT_DIR / "logs.txt"

GITHUB_API_LATEST = "https://api.github.com/repos/NVIDIA-RTX/Streamline/releases/latest"

FORCE_UPDATE = False
