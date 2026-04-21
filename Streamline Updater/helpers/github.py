import requests
import re
from helpers.config import GITHUB_API_LATEST

def get_latest_release():
    r = requests.get(GITHUB_API_LATEST)
    r.raise_for_status()
    data = r.json()

    tag = data["tag_name"]
    version = tag.lstrip("v")

    asset_url = None

    for asset in data["assets"]:
        if re.match(r"^streamline-sdk-v\d+\.\d+\.\d+\.zip$", asset["name"]):
            asset_url = asset["browser_download_url"]
            break

    if not asset_url:
        raise RuntimeError("No valid SDK asset found")

    return version, asset_url
