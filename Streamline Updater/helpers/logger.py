from helpers.config import LOG_FILE

# ANSI color codes (Windows 10+ supported)
COLORS = {
    "INFO": "\033[37m",     # white
    "WARNING": "\033[33m",  # yellow
    "ERROR": "\033[31m",    # red
    "SUCCESS": "\033[32m",  # green
}
RESET = "\033[0m"


def log(msg, level="INFO"):
    color = COLORS.get(level, COLORS["INFO"])
    line = f"[{level}] {msg}"

    # Console output (colored)
    print(f"{color}{line}{RESET}")

    # File output (no color)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
