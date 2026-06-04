import hashlib
import os

import win32api

from helpers.logger import log


def get_file_version(path):
    """Read the Windows PE file version as a 4-tuple, or None if unavailable."""
    try:
        info = win32api.GetFileVersionInfo(str(path), "\\")

        ms = info['FileVersionMS']
        ls = info['FileVersionLS']

        return (
            (ms >> 16) & 0xFFFF,
            ms & 0xFFFF,
            (ls >> 16) & 0xFFFF,
            ls & 0xFFFF
        )

    except Exception as e:
        log(f"Could not read version info for {path}: {e}", "WARNING")
        return None


def sha256(path):
    """Stream a file and return its SHA-256 hex digest."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def remove_motw(path):
    """Remove the Zone.Identifier ADS (Mark of the Web) from a file, if present."""
    ads = str(path) + ":Zone.Identifier"
    try:
        if os.path.exists(ads):
            os.remove(ads)
    except Exception:
        pass
