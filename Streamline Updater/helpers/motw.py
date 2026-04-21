import os

def remove_motw(path):
    ads = str(path) + ":Zone.Identifier"
    try:
        if os.path.exists(ads):
            os.remove(ads)
    except Exception:
        pass
