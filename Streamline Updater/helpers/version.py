import win32api


def get_file_version(path):
    try:
        info = win32api.GetFileVersionInfo(str(path), "\\")

        ms = info['FileVersionMS']
        ls = info['FileVersionLS']

        return (
            (ms >> 16) & 0xFFFF,
            ms & 0xFFFF,
            (ls >> 16) & 0xFFFF,
            ls & 0xFFFF
        )

    except Exception as e:
        # DEBUG: temporarily print error
        print(f"[VERSION ERROR] {path}: {e}")
        return None
