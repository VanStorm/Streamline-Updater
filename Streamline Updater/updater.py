from helpers.github import get_latest_release
from helpers.sdk import download_and_extract
from helpers.steam import get_steam_games
from helpers.epic import get_epic_games
from helpers.gog import get_gog_games
from helpers.scanner import find_dll_dirs
from helpers.deploy import deploy_directory
from helpers.config import SDK_DIR
from helpers.logger import log
from helpers.version import get_file_version

import sys


def choose_mode():
    print("1) Dry Run")
    print("2) Deploy")
    return input("Select: ").strip()


def format_version(v):
    if not v:
        return "unknown"
    return ".".join(str(x) for x in v)


def get_game_version(dirs):
    """
    Determine the highest Streamline version found in a game.
    """
    versions = []

    for d in dirs:
        for dll in d["dll_files"]:
            path = d["path"] + "\\" + dll
            v = get_file_version(path)
            if v:
                versions.append(v)

    if not versions:
        return None

    return max(versions)


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


def main():
    from helpers import config

    if "--force" in sys.argv:
        config.FORCE_UPDATE = True
        log("Force mode enabled")

    mode = choose_mode()
    dry_run = (mode == "1")

    version, url = get_latest_release()
    download_and_extract(version, url)

    sdk_path = SDK_DIR / version

    # Discover games
    games = get_steam_games() + get_epic_games() + get_gog_games()

    # Deduplicate games by path
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
        print("No games with Streamline DLLs detected.")
        return

    # User selection
    selected_games = select_games(game_map)

    # Deployment
    for g in selected_games:
        log(f"\nProcessing: {g['name']} ({g['launcher']})")

        # Deduplicate directories (case-insensitive)
        unique_dirs = {
            d["path"].lower(): d for d in g["dirs"]
        }.values()

        for d in unique_dirs:
            deploy_directory(d, sdk_path, dry_run)


if __name__ == "__main__":
    main()
