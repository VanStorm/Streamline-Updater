from helpers.github import get_latest_release
from helpers.sdk import download_and_extract
from helpers.steam import get_steam_games
from helpers.epic import get_epic_games
from helpers.gog import get_gog_games
from helpers.scanner import find_dll_dirs
from helpers.deploy import deploy_directory
from helpers.config import SDK_DIR, FORCE_UPDATE
from helpers.logger import log

import sys


def choose_mode():
    print("1) Dry Run")
    print("2) Deploy")
    return input("Select: ").strip()


def main():
    global FORCE_UPDATE

    if "--force" in sys.argv:
        from helpers import config
        config.FORCE_UPDATE = True

    mode = choose_mode()
    dry_run = (mode == "1")

    version, url = get_latest_release()
    download_and_extract(version, url)

    sdk_path = SDK_DIR / version

    games = get_steam_games() + get_epic_games() + get_gog_games()

    all_dirs = []
    for g in games:
        dirs = find_dll_dirs(g["path"])
        all_dirs.extend(dirs)

    unique_dirs = {d["path"]: d for d in all_dirs}.values()

    for d in unique_dirs:
        deploy_directory(d, sdk_path, dry_run)


if __name__ == "__main__":
    main()
