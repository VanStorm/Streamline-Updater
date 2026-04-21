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

    seen_paths = set()

    i = 0
    while True:
        try:
            subkey_name = winreg.EnumKey(root, i)
            subkey = winreg.OpenKey(root, subkey_name)

            try:
                path = winreg.QueryValueEx(subkey, "path")[0]
                name = winreg.QueryValueEx(subkey, "gameName")[0]

                # ---- DLC handling ----
                # Skip only if dependsOn exists AND is non-empty
                try:
                    depends_on = winreg.QueryValueEx(subkey, "dependsOn")[0]
                    if depends_on:
                        i += 1
                        continue
                except FileNotFoundError:
                    # No dependsOn key → base game
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
                # Missing expected keys (path/gameName), skip safely
                pass

            i += 1

        except OSError:
            # No more subkeys
            break

    return games
