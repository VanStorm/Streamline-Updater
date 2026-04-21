import json
from pathlib import Path


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
                    "launcher": "epic",
                    "path": path
                })
        except:
            continue

    return games
