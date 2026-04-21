from helpers.config import LOG_FILE

def log(msg, level="INFO"):
    line = f"[{level}] {msg}"
    print(line)

    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
