import winreg
from pathlib import Path


def parse_acf(path):
    data = {}
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            parts = line.strip().split('"')
            if len(parts) >= 4:
                data[parts[1]] = parts[3]
    return data


def get_steam_libraries():
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
    install_path = winreg.QueryValueEx(key, "SteamPath")[0]

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

    for lib in get_steam_libraries():
        manifest_dir = lib / "steamapps"
        if not manifest_dir.exists():
            continue

        for f in manifest_dir.glob("appmanifest_*.acf"):
            data = parse_acf(f)
            installdir = data.get("installdir")
            name = data.get("name", installdir)

            if installdir:
                path = lib / "steamapps" / "common" / installdir
                if path.exists():
                    games.append({
                        "id": f.stem,
                        "name": name,
                        "launcher": "steam",
                        "path": str(path)
                    })

    return games
