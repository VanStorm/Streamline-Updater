import json
import re
import time
import requests
import zipfile
import shutil
import os
from pathlib import Path

from helpers.config import SDK_DIR, GITHUB_API_LATEST, CACHE_FILE
from helpers.logger import log
from helpers.fileutils import remove_motw


# Cache is valid for 1 hour
CACHE_TTL_SECONDS = 3600

REQUIRED_DLLS = [
    "sl.common.dll",
    "sl.deepdvc.dll",
    "sl.directsr.dll",
    "sl.dlss.dll",
    "sl.dlss_d.dll",
    "sl.dlss_g.dll",
    "sl.interposer.dll",
    "sl.nis.dll",
    "sl.nvperf.dll",
    "sl.pcl.dll",
    "sl.reflex.dll",
]

STRICT_VALIDATION = True


def _load_cache():
    try:
        if CACHE_FILE.exists():
            data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            if time.time() - data.get("timestamp", 0) < CACHE_TTL_SECONDS:
                return data.get("payload")
    except Exception:
        pass
    return None


def _save_cache(payload):
    try:
        CACHE_FILE.write_text(
            json.dumps({"timestamp": time.time(), "payload": payload}),
            encoding="utf-8"
        )
    except Exception:
        pass


def get_latest_release():
    cached = _load_cache()

    if cached:
        log("Using cached GitHub release info")
        data = cached
    else:
        r = requests.get(GITHUB_API_LATEST, timeout=30)
        r.raise_for_status()
        data = r.json()
        _save_cache(data)

    tag = data["tag_name"]
    version = tag.lstrip("v")

    asset_url = None

    for asset in data["assets"]:
        if re.match(r"^streamline-sdk-v\d+\.\d+\.\d+\.zip$", asset["name"]):
            asset_url = asset["browser_download_url"]
            break

    if not asset_url:
        raise RuntimeError("No valid SDK asset found")

    return version, asset_url


def sdk_exists(version):
    path = SDK_DIR / version
    return path.exists() and validate_sdk(path)


def validate_sdk(path: Path):
    present = {p.name.lower() for p in path.glob("sl.*.dll")}

    if STRICT_VALIDATION:
        return all(dll in present for dll in REQUIRED_DLLS)

    return "sl.common.dll" in present and len(present) >= 2


def download_and_extract(version, url):
    SDK_DIR.mkdir(exist_ok=True)
    extract_dir = SDK_DIR / version

    if sdk_exists(version):
        log(f"SDK {version} already present, skipping download")
        return

    def attempt():
        zip_path = SDK_DIR / f"{version}.zip"

        log(f"Downloading SDK {version}")
        r = requests.get(url, stream=True, timeout=30)
        r.raise_for_status()

        with open(zip_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        if extract_dir.exists():
            shutil.rmtree(extract_dir, ignore_errors=True)

        extract_dir.mkdir()

        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(extract_dir)

        # flatten the bin/x64 DLLs up to the version root
        for root, _, files in os.walk(extract_dir):
            if root.endswith("bin\\x64") or root.endswith("bin/x64"):
                for file in files:
                    if file.lower().startswith("sl.") and file.lower().endswith(".dll"):
                        src = Path(root) / file
                        dst = extract_dir / file
                        shutil.copy2(src, dst)
                        remove_motw(dst)

        # strip everything that isn't an sl.*.dll
        for item in extract_dir.iterdir():
            if item.is_file():
                if not (item.name.lower().startswith("sl.") and item.name.lower().endswith(".dll")):
                    item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)

        zip_path.unlink(missing_ok=True)

    attempt()

    if not validate_sdk(extract_dir):
        log(f"SDK {version} invalid (missing DLLs), retrying...", "WARNING")

        shutil.rmtree(extract_dir, ignore_errors=True)

        attempt()

        if not validate_sdk(extract_dir):
            missing = [
                dll for dll in REQUIRED_DLLS
                if not (extract_dir / dll).exists()
            ]
            raise RuntimeError(
                f"SDK {version} is corrupted after re-download. Missing: {missing}"
            )

    dll_count = len(list(extract_dir.glob("sl.*.dll")))
    log(f"SDK {version} ready ({dll_count} DLLs)")
