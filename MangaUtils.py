import os
import errno


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise

def removeInvalidCharacters(path):
    invalidChars = "<>:\"/\\|?*"

    return ''.join(c for c in path if c not in invalidChars)

def cbzdir(path, cbz):
    for root, dirs, files in os.walk(path):
        for file in files:
            cbzFileItem = os.path.join(root, file)
            cbz.write(cbzFileItem, os.path.relpath(cbzFileItem, os.path.join(path, '.')))
