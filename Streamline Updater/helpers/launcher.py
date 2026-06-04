import json
import winreg
from pathlib import Path

from helpers.logger import log


def parse_acf(path):
    data = {}
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            parts = line.strip().split('"')
            if len(parts) >= 4:
                data[parts[1]] = parts[3]
    return data


def get_steam_libraries():
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
    games = []
    seen = set()

    for lib in get_steam_libraries():
        manifest_dir = lib / "steamapps"
        if not manifest_dir.exists():
            continue

        for f in manifest_dir.glob("appmanifest_*.acf"):
            data = parse_acf(f)

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
                        "path": str(path)
                    })

    return games


def get_epic_games():
    base = Path(r"C:\ProgramData\Epic\EpicGamesLauncher\Data\Manifests")
    games = []

    if not base.exists():
        return games

    for f in base.glob("*.item"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))

            path = data.get("InstallLocation")
            name = data.get("DisplayName")

            if path and Path(path).exists():
                games.append({
                    "id": f.stem,
                    "name": name,
                    "launcher": "Epic Games",
                    "path": path
                })
        except Exception:
            continue

    return games


def get_gog_games():
    games = []

    try:
        root = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WOW6432Node\GOG.com\Games"
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
                path = winreg.QueryValueEx(subkey, "path")[0]
                name = winreg.QueryValueEx(subkey, "gameName")[0]

                # GOG lists DLC as separate keys that point at the base game's
                # folder; skip them so we don't process the same path twice
                try:
                    depends_on = winreg.QueryValueEx(subkey, "dependsOn")[0]
                    if depends_on:
                        i += 1
                        continue
                except FileNotFoundError:
                    pass

                resolved = str(Path(path).resolve()).lower()

                if Path(path).exists() and resolved not in seen_paths:
                    seen_paths.add(resolved)

                    games.append({
                        "id": subkey_name,
                        "name": name,
                        "launcher": "GOG",
                        "path": path
                    })

            except FileNotFoundError:
                # entry missing path/gameName
                pass

            i += 1

        except OSError:
            break

    return games


def discover_games():
    """Discover games across all supported launchers, deduplicated by path."""
    games = get_steam_games() + get_epic_games() + get_gog_games()

    seen_paths = set()
    unique_games = []

    for g in games:
        key = g["path"].lower()
        if key not in seen_paths:
            seen_paths.add(key)
            unique_games.append(g)

    return unique_games
