"""Streamline-Updater — single-file CLI tool by VanStorm.

Scans installed games across Steam, Epic Games, and GOG for NVIDIA Streamline
DLLs (sl.*.dll) and updates them to the latest official SDK release from
https://github.com/NVIDIA-RTX/Streamline/

Usage:
    python updater.py              # normal run
    python updater.py --force      # force-update regardless of version
    python updater.py --no-pause   # skip exit prompt (automation)
"""

# =============================================================================
# Imports
# =============================================================================

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time
import winreg
import zipfile
from datetime import datetime
from pathlib import Path

import requests
import win32api

# =============================================================================
# Configuration
# =============================================================================

if getattr(sys, "frozen", False):
    ROOT_DIR = Path(sys.executable).resolve().parent
else:
    ROOT_DIR = Path(__file__).resolve().parent

SDK_DIR = ROOT_DIR / "streamline-sdk"
CACHE_FILE = ROOT_DIR / "cache.json"
LOG_FILE = ROOT_DIR / "logs.txt"

GITHUB_API_LATEST = "https://api.github.com/repos/NVIDIA-RTX/Streamline/releases/latest"

FORCE_UPDATE = False

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

# =============================================================================
# Logger
# =============================================================================

_COLORS = {
    "INFO": "\033[37m",
    "WARNING": "\033[33m",
    "ERROR": "\033[31m",
    "SUCCESS": "\033[32m",
}
_RESET = "\033[0m"


def log(msg, level="INFO"):
    """Log a message to both the console (colored) and the log file (timestamped)."""
    color = _COLORS.get(level, _COLORS["INFO"])
    line = f"[{level}] {msg}"

    print(f"{color}{line}{_RESET}")

    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {line}\n")
    except Exception:
        pass


# =============================================================================
# File Utilities
# =============================================================================

def get_file_version(path):
    """Read the Windows PE file version as a 4-tuple, or None if unavailable."""
    try:
        info = win32api.GetFileVersionInfo(str(path), "\\")
        ms = info["FileVersionMS"]
        ls = info["FileVersionLS"]
        return (
            (ms >> 16) & 0xFFFF,
            ms & 0xFFFF,
            (ls >> 16) & 0xFFFF,
            ls & 0xFFFF,
        )
    except Exception as e:
        log(f"Could not read version info for {path}: {e}", "WARNING")
        return None


def format_version(version_tuple):
    """Format a version tuple like (2, 6, 1, 0) into '2.6.1.0', or 'unknown'."""
    if not version_tuple:
        return "unknown"
    return ".".join(str(x) for x in version_tuple)


def sha256(path):
    """Return the SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def remove_motw(path):
    """Remove the Zone.Identifier ADS (Mark of the Web) to avoid SmartScreen warnings."""
    ads = str(path) + ":Zone.Identifier"
    try:
        if os.path.exists(ads):
            os.remove(ads)
    except Exception:
        pass


# =============================================================================
# SDK — GitHub Release & Download
# =============================================================================

def _load_cache():
    """Load the cached GitHub API response if still within the TTL window."""
    try:
        if CACHE_FILE.exists():
            data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            if time.time() - data.get("timestamp", 0) < CACHE_TTL_SECONDS:
                return data.get("payload")
    except Exception:
        pass
    return None


def _save_cache(payload):
    """Persist the GitHub API response with a timestamp for TTL checking."""
    try:
        CACHE_FILE.write_text(
            json.dumps({"timestamp": time.time(), "payload": payload}),
            encoding="utf-8",
        )
    except Exception:
        pass


def get_latest_release():
    """Fetch the latest Streamline SDK release tag and asset URL from GitHub.

    Returns:
        Tuple of (version_string, download_url).

    Raises:
        RuntimeError: If no valid SDK zip asset is found.
        requests.HTTPError: If the GitHub API call fails.
    """
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
        raise RuntimeError("No valid SDK asset found in the latest GitHub release")

    return version, asset_url


def validate_sdk(path):
    """Validate that the extracted SDK contains all required DLLs."""
    present = {p.name.lower() for p in path.glob("sl.*.dll")}

    if STRICT_VALIDATION:
        return all(dll in present for dll in REQUIRED_DLLS)

    return "sl.common.dll" in present and len(present) >= 2


def sdk_exists(version):
    """Check if a valid, extracted SDK for the given version already exists."""
    path = SDK_DIR / version
    return path.exists() and validate_sdk(path)


def _extract_sdk(version, url):
    """Download the SDK zip and extract DLLs, flattening bin/x64 to the version root."""
    extract_dir = SDK_DIR / version
    zip_path = SDK_DIR / f"{version}.zip"

    log(f"Downloading SDK {version}")
    r = requests.get(url, stream=True, timeout=60)
    r.raise_for_status()

    with open(zip_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    if extract_dir.exists():
        shutil.rmtree(extract_dir, ignore_errors=True)

    extract_dir.mkdir()

    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(extract_dir)

    # Flatten: pull sl.*.dll from nested bin/x64 up to version root
    bin_x64 = extract_dir / "bin" / "x64"
    if bin_x64.exists():
        for dll_file in bin_x64.iterdir():
            if dll_file.name.lower().startswith("sl.") and dll_file.name.lower().endswith(".dll"):
                dst = extract_dir / dll_file.name
                shutil.copy2(dll_file, dst)
                remove_motw(dst)

    # Strip everything that isn't an sl.*.dll
    for item in list(extract_dir.iterdir()):
        if item.is_file():
            if not (item.name.lower().startswith("sl.") and item.name.lower().endswith(".dll")):
                item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)

    zip_path.unlink(missing_ok=True)


def download_and_extract(version, url):
    """Download, extract, and validate the SDK. Retries once on validation failure.

    Raises:
        RuntimeError: If the SDK is still invalid after a retry.
    """
    SDK_DIR.mkdir(exist_ok=True)
    extract_dir = SDK_DIR / version

    if sdk_exists(version):
        log(f"SDK {version} already present, skipping download")
        return

    _extract_sdk(version, url)

    if not validate_sdk(extract_dir):
        log(f"SDK {version} invalid (missing DLLs), retrying download...", "WARNING")
        shutil.rmtree(extract_dir, ignore_errors=True)

        _extract_sdk(version, url)

        if not validate_sdk(extract_dir):
            missing = [dll for dll in REQUIRED_DLLS if not (extract_dir / dll).exists()]
            raise RuntimeError(
                f"SDK {version} is corrupted after re-download. Missing: {missing}"
            )

    dll_count = len(list(extract_dir.glob("sl.*.dll")))
    log(f"SDK {version} ready ({dll_count} DLLs)", "SUCCESS")


# =============================================================================
# Launcher Discovery
# =============================================================================

def _parse_acf(path):
    """Parse a Steam ACF (Valve KeyValues) file into a flat key-value dict."""
    data = {}
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            parts = line.strip().split('"')
            if len(parts) >= 4:
                data[parts[1]] = parts[3]
    return data


def _get_steam_libraries():
    """Return a list of Steam library folder Paths."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
        install_path = winreg.QueryValueEx(key, "SteamPath")[0]
    except (FileNotFoundError, OSError):
        return []

    libs = [Path(install_path)]

    vdf = Path(install_path) / "steamapps" / "libraryfolders.vdf"
    if vdf.exists():
        with open(vdf, encoding="utf-8", errors="ignore") as f:
            for line in f:
                if '"path"' in line:
                    libs.append(Path(line.split('"')[3]))

    return libs


def get_steam_games():
    """Discover installed Steam games by reading appmanifest ACF files."""
    games = []
    seen = set()

    for lib in _get_steam_libraries():
        manifest_dir = lib / "steamapps"
        if not manifest_dir.exists():
            continue

        for f in manifest_dir.glob("appmanifest_*.acf"):
            data = _parse_acf(f)

            installdir = data.get("installdir")
            name = data.get("name", installdir)

            if installdir:
                path = (lib / "steamapps" / "common" / installdir).resolve()

                key = str(path).lower()
                if path.exists() and key not in seen:
                    seen.add(key)
                    games.append({
                        "id": f.stem,
                        "name": name,
                        "launcher": "Steam",
                        "path": path,
                    })

    return games


def get_epic_games():
    """Discover installed Epic Games by reading manifest .item files."""
    program_data = Path(os.environ.get("ProgramData", r"C:\ProgramData"))
    base = program_data / "Epic" / "EpicGamesLauncher" / "Data" / "Manifests"
    games = []

    if not base.exists():
        return games

    for f in base.glob("*.item"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))

            install_location = data.get("InstallLocation")
            name = data.get("DisplayName")

            if install_location:
                path = Path(install_location).resolve()
                if path.exists():
                    games.append({
                        "id": f.stem,
                        "name": name,
                        "launcher": "Epic Games",
                        "path": path,
                    })
        except Exception:
            continue

    return games


def get_gog_games():
    """Discover installed GOG games by enumerating GOG registry keys."""
    games = []

    try:
        root = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WOW6432Node\GOG.com\Games",
        )
    except FileNotFoundError:
        return games

    seen_paths = set()

    i = 0
    while True:
        try:
            subkey_name = winreg.EnumKey(root, i)
            subkey = winreg.OpenKey(root, subkey_name)

            try:
                path_str = winreg.QueryValueEx(subkey, "path")[0]
                name = winreg.QueryValueEx(subkey, "gameName")[0]

                # Skip DLC entries that point at the base game's folder
                try:
                    depends_on = winreg.QueryValueEx(subkey, "dependsOn")[0]
                    if depends_on:
                        i += 1
                        continue
                except FileNotFoundError:
                    pass

                path = Path(path_str).resolve()
                resolved_key = str(path).lower()

                if path.exists() and resolved_key not in seen_paths:
                    seen_paths.add(resolved_key)
                    games.append({
                        "id": subkey_name,
                        "name": name,
                        "launcher": "GOG",
                        "path": path,
                    })

            except FileNotFoundError:
                pass

            i += 1

        except OSError:
            break

    return games


def discover_games():
    """Discover games across all supported launchers, deduplicated by resolved path."""
    all_games = get_steam_games() + get_epic_games() + get_gog_games()

    seen_paths = set()
    unique_games = []

    for game in all_games:
        key = str(game["path"]).lower()
        if key not in seen_paths:
            seen_paths.add(key)
            unique_games.append(game)

    log(f"Discovered {len(unique_games)} games across all launchers")
    return unique_games


# =============================================================================
# Deployment
# =============================================================================

def deploy_directory(dir_info, sdk_path, dry_run=False):
    """Deploy updated DLLs to a single game directory.

    Compares versions via PE metadata (with SHA-256 fallback) and performs
    atomic replacement: .tmp -> .bak -> swap.

    Returns True on success, False if a fatal error occurred for this directory.
    """
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

            # Skip if the game already has this version or newer
            if not FORCE_UPDATE and existing_version and sdk_version:
                if existing_version > sdk_version:
                    log(f"Skipping newer DLL: {dst} ({existing_str} > {sdk_str})")
                    continue

                if existing_version == sdk_version:
                    log(f"Up-to-date: {dst} ({existing_str})")
                    continue

            # No version metadata — fall back to hash comparison
            if not FORCE_UPDATE:
                if existing_version is None or sdk_version is None:
                    try:
                        if sha256(src) == sha256(dst):
                            log(f"Up-to-date (hash): {dst}")
                            continue
                    except Exception:
                        pass

            if dry_run:
                log(f"[DRY] Would update {dst} ({existing_str} -> {sdk_str})")
                continue

            # Atomic replacement: .tmp -> back up old to .bak -> swap in new
            tmp = dst.with_suffix(".tmp")
            bak = dst.with_suffix(".bak")

            try:
                shutil.copy2(src, tmp)

                if dst.exists():
                    os.replace(dst, bak)

                os.replace(tmp, dst)

                log(f"Updated {dst} ({existing_str} -> {sdk_str})", "SUCCESS")

            except PermissionError:
                log(f"Locked file, skipping directory: {dst}", "WARNING")
                if tmp.exists():
                    tmp.unlink(missing_ok=True)
                return False

        except Exception as e:
            log(f"Error processing {dst}: {e}", "ERROR")
            return False

    return True


# =============================================================================
# CLI Interface
# =============================================================================

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="Streamline-Updater",
        description="Update NVIDIA Streamline DLLs in installed games to the latest SDK version.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force-update all DLLs regardless of version comparison.",
    )
    parser.add_argument(
        "--no-pause",
        action="store_true",
        help="Skip the 'Press Enter to exit' prompt (for automation or scripts).",
    )
    return parser.parse_args()


def find_dll_dirs(game_path):
    """Walk a game directory to find folders containing Streamline DLLs.

    Stops descending into subdirectories once a Streamline directory is found,
    keeping scan times short for large game installs.
    """
    results = []

    for root, dirs, files in os.walk(game_path):
        files_lower = [f.lower() for f in files]

        has_common = "sl.common.dll" in files_lower
        has_dlss = "sl.dlss.dll" in files_lower

        if has_common or has_dlss:
            matches = [
                f for f in files
                if f.lower().startswith("sl.") and f.lower().endswith(".dll")
            ]

            results.append({
                "path": str(root),
                "dll_files": matches,
                "has_common": has_common,
                "has_dlss": has_dlss,
            })

            # Don't recurse past a folder that already has the DLLs
            dirs.clear()

    return results


def choose_mode():
    """Display the mode selection menu and return the user's choice."""
    print("\n======================================")
    print("  Streamline SDK Updater by VanStorm")
    print("======================================\n")

    print("1) Test Deployment (no files will get changed)")
    print("2) Deployment (Streamline DLLs will be updated to the latest version)\n")

    choice = input("Select an option: ").strip()

    if choice not in ("1", "2"):
        print("Invalid selection. Exiting.")
        sys.exit(0)

    return choice


def get_game_version(dirs):
    """Determine the highest Streamline version across a game's DLL directories."""
    versions = []

    for d in dirs:
        for dll in d["dll_files"]:
            path = Path(d["path"]) / dll
            v = get_file_version(path)
            if v:
                versions.append(v)

    return max(versions) if versions else None


def display_games(game_map):
    """Print the detected games with their current Streamline versions."""
    print("\nDetected games with Streamline:\n")

    for i, game in enumerate(game_map, 1):
        version_str = format_version(game["version"])
        print(f"{i}) {game['name']} ({game['launcher']}) (SL SDK {version_str})")

    print("\n0) All games")


def select_games(game_map):
    """Interactive game selection — returns the list of games the user chose."""
    display_games(game_map)

    selection = input("\nSelect games (e.g. 1,3,5 or 0 for all): ").strip()

    if selection == "0":
        selected = game_map
    else:
        indices = set()

        for part in selection.split(","):
            try:
                idx = int(part.strip()) - 1
                if 0 <= idx < len(game_map):
                    indices.add(idx)
            except ValueError:
                continue

        selected = [game_map[i] for i in sorted(indices)]

    if not selected:
        print("No valid selection. Exiting.")
        sys.exit(0)

    print("\nSelected games:\n")
    for game in selected:
        version_str = format_version(game["version"])
        print(f"- {game['name']} ({game['launcher']}) (SL SDK {version_str})")

    confirm = input("\nProceed? (y/n): ").strip().lower()
    if confirm != "y":
        print("Aborted.")
        sys.exit(0)

    return selected


def wait_if_exe(no_pause):
    """Pause before exit when running as a PyInstaller EXE (unless --no-pause)."""
    if getattr(sys, "frozen", False) and not no_pause:
        input("\nPress Enter to exit...")


# =============================================================================
# Main
# =============================================================================

def main(args):
    """Main orchestration flow."""
    global FORCE_UPDATE

    if args.force:
        FORCE_UPDATE = True
        log("Force mode enabled", "WARNING")

    mode = choose_mode()
    dry_run = (mode == "1")

    if dry_run:
        log("Mode: TEST DEPLOYMENT (no files will be changed)", "WARNING")
    else:
        log("Mode: DEPLOYMENT (files WILL be modified)", "WARNING")

    sdk_version, sdk_url = get_latest_release()
    download_and_extract(sdk_version, sdk_url)

    sdk_path = SDK_DIR / sdk_version

    log(f"SDK version: {sdk_version}")
    log(f"Working directory: {ROOT_DIR}")

    unique_games = discover_games()

    game_map = []

    for game in unique_games:
        dirs = find_dll_dirs(game["path"])

        if dirs:
            game_version = get_game_version(dirs)

            game_map.append({
                "name": game["name"],
                "launcher": game["launcher"],
                "path": game["path"],
                "dirs": dirs,
                "version": game_version,
            })

    if not game_map:
        log("No games with Streamline DLLs detected.", "WARNING")
        return

    selected_games = select_games(game_map)

    for game in selected_games:
        log(f"\nProcessing: {game['name']} ({game['launcher']})", "SUCCESS")

        # Deduplicate directories by lowercased path
        unique_dirs = {d["path"].lower(): d for d in game["dirs"]}.values()

        for d in unique_dirs:
            deploy_directory(d, sdk_path, dry_run)

    log(f"\nFinished. Logs written to: {LOG_FILE}", "SUCCESS")


if __name__ == "__main__":
    args = parse_args()
    try:
        main(args)
    except KeyboardInterrupt:
        log("\nInterrupted by user.", "WARNING")
    except Exception as e:
        log(f"Fatal error: {e}", "ERROR")
    finally:
        wait_if_exe(args.no_pause)
