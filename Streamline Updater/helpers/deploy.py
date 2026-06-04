import os
from pathlib import Path
import shutil

from helpers import config
from helpers.fileutils import sha256, get_file_version
from helpers.logger import log


def format_version(v):
    if not v:
        return "no-version"
    return ".".join(str(x) for x in v)


def deploy_directory(dir_info, sdk_path, dry_run=False):
    path = Path(dir_info["path"])

    for dll in dir_info["dll_files"]:
        src = sdk_path / dll
        dst = path / dll

        if not src.exists():
            continue

        try:
            existing_version = get_file_version(dst)
            sdk_version = get_file_version(src)

            existing_str = format_version(existing_version)
            sdk_str = format_version(sdk_version)

            # skip if the game already has this version or a newer one
            if not config.FORCE_UPDATE and existing_version and sdk_version:
                if existing_version > sdk_version:
                    log(f"Skipping newer DLL: {dst} ({existing_str} > {sdk_str})")
                    continue

                if existing_version == sdk_version:
                    log(f"Up-to-date: {dst} ({existing_str})")
                    continue

            # no version metadata to compare, fall back to hashing
            if not config.FORCE_UPDATE:
                if existing_version is None or sdk_version is None:
                    try:
                        if sha256(src) == sha256(dst):
                            log(f"Up-to-date (hash): {dst}")
                            continue
                    except Exception:
                        pass

            if dry_run:
                log(f"[DRY] Would update {dst} ({existing_str} → {sdk_str})")
                continue

            # copy to .tmp, back up the old DLL, then swap in the new one
            tmp = dst.with_suffix(".tmp")
            bak = dst.with_suffix(".bak")

            try:
                shutil.copy2(src, tmp)

                if dst.exists():
                    os.replace(dst, bak)

                os.replace(tmp, dst)

                log(f"Updated {dst} ({existing_str} → {sdk_str})")

            except PermissionError:
                log(f"Locked file, skipping directory: {dst}", "WARNING")
                return False

        except Exception as e:
            log(f"Error processing {dst}: {e}", "ERROR")
            return False

    return True
