from helpers.github import get_latest_release
from helpers.sdk import download_and_extract
from helpers.steam import get_steam_games
from helpers.epic import get_epic_games
from helpers.gog import get_gog_games
from helpers.scanner import find_dll_dirs
from helpers.deploy import deploy_directory
from helpers.config import SDK_DIR, LOG_FILE
from helpers.logger import log
from helpers.version import get_file_version

import sys


# ----------------------------
# UI / Mode Selection
# ----------------------------
def choose_mode():
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


# ----------------------------
# Helpers
# ----------------------------
def format_version(v):
    if not v:
        return "unknown"
    return ".".join(str(x) for x in v)


def get_game_version(dirs):
    versions = []

    for d in dirs:
        for dll in d["dll_files"]:
            path = d["path"] + "\\" + dll
            v = get_file_version(path)
            if v:
                versions.append(v)

    return max(versions) if versions else None


def display_games(game_map):
    print("\nDetected games with Streamline:\n")

    for i, g in enumerate(game_map, 1):
        version_str = format_version(g["version"])
        print(f"{i}) {g['name']} ({g['launcher']}) (SL SDK {version_str})")

    print("\n0) All games")


def select_games(game_map):
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
    for g in selected:
        version_str = format_version(g["version"])
        print(f"- {g['name']} ({g['launcher']}) (SL SDK {version_str})")

    confirm = input("\nProceed? (y/n): ").strip().lower()
    if confirm != "y":
        print("Aborted.")
        sys.exit(0)

    return selected


# ----------------------------
# Pause for EXE
# ----------------------------
def wait_if_exe():
    if getattr(sys, "frozen", False) and "--no-pause" not in sys.argv:
        input("\nPress Enter to exit...")


# ----------------------------
# Main Logic
# ----------------------------
def main():
    from helpers import config

    # Force flag
    if "--force" in sys.argv:
        config.FORCE_UPDATE = True
        log("Force mode enabled", "WARNING")

    # Mode selection
    mode = choose_mode()
    dry_run = (mode == "1")

    if dry_run:
        log("Mode: TEST DEPLOYMENT (no files will be changed)", "WARNING")
    else:
        log("Mode: DEPLOYMENT (files WILL be modified)", "WARNING")

    # Download SDK
    version, url = get_latest_release()
    download_and_extract(version, url)

    sdk_path = SDK_DIR / version

    log(f"Using working directory: {SDK_DIR.parent}", "INFO")

    # Discover games
    games = get_steam_games() + get_epic_games() + get_gog_games()

    # Deduplicate by path
    seen_paths = set()
    unique_games = []

    for g in games:
        key = g["path"].lower()
        if key not in seen_paths:
            seen_paths.add(key)
            unique_games.append(g)

    # Build game map
    game_map = []

    for g in unique_games:
        dirs = find_dll_dirs(g["path"])

        if dirs:
            version = get_game_version(dirs)

            game_map.append({
                "name": g["name"],
                "launcher": g["launcher"],
                "path": g["path"],
                "dirs": dirs,
                "version": version
            })

    if not game_map:
        log("No games with Streamline DLLs detected.", "WARNING")
        return

    # User selection
    selected_games = select_games(game_map)

    # Deployment
    for g in selected_games:
        log(f"\nProcessing: {g['name']} ({g['launcher']})", "SUCCESS")

        unique_dirs = {
            d["path"].lower(): d for d in g["dirs"]
        }.values()

        for d in unique_dirs:
            deploy_directory(d, sdk_path, dry_run)

    log(f"\nFinished. Logs written to: {LOG_FILE}", "SUCCESS")


# ----------------------------
# Entry Point
# ----------------------------
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"Fatal error: {e}", "ERROR")
    finally:
        wait_if_exe()
