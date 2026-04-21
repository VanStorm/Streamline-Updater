import os

def find_dll_dirs(game_path):
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
                "path": root,
                "dll_files": matches,
                "has_common": has_common,
                "has_dlss": has_dlss
            })

            # stop descending into this directory
            dirs[:] = []

    return results
