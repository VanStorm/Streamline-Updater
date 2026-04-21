import winreg
from pathlib import Path


def get_gog_games():
    games = []

    try:
        root = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WOW6432Node\GOG.com\Games"
        )
    except FileNotFoundError:
        return games

    i = 0
    while True:
        try:
            subkey_name = winreg.EnumKey(root, i)
            subkey = winreg.OpenKey(root, subkey_name)

            try:
                path = winreg.QueryValueEx(subkey, "path")[0]
                if Path(path).exists():
                    games.append({
                        "id": subkey_name,
                        "name": subkey_name,
                        "launcher": "gog",
                        "path": path
                    })
            except FileNotFoundError:
                pass

            i += 1

        except OSError:
            break

    return games
