import requests
import zipfile
import shutil
import os
from pathlib import Path

from helpers.config import SDK_DIR
from helpers.logger import log
from helpers.motw import remove_motw


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
        r = requests.get(url)
        r.raise_for_status()

        with open(zip_path, "wb") as f:
            f.write(r.content)

        if extract_dir.exists():
            shutil.rmtree(extract_dir, ignore_errors=True)

        extract_dir.mkdir()

        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(extract_dir)

        # Copy DLLs
        for root, _, files in os.walk(extract_dir):
            if root.endswith("bin\\x64") or root.endswith("bin/x64"):
                for file in files:
                    if file.lower().startswith("sl.") and file.lower().endswith(".dll"):
                        src = Path(root) / file
                        dst = extract_dir / file
                        shutil.copy2(src, dst)
                        remove_motw(dst)

        # Cleanup
        for item in extract_dir.iterdir():
            if item.is_file():
                if not (item.name.lower().startswith("sl.") and item.name.lower().endswith(".dll")):
                    item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)

        zip_path.unlink(missing_ok=True)

    # Attempt 1
    attempt()

    if not validate_sdk(extract_dir):
        log(f"SDK {version} invalid (missing DLLs), retrying...", "WARNING")

        shutil.rmtree(extract_dir, ignore_errors=True)

        # Attempt 2
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
