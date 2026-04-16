import os
from pathlib import Path


REPO_DIR = Path(__file__).resolve().parent


def get_db_path():
    override = os.environ.get('DB_PATH')
    if override:
        path = Path(override).expanduser()
        if not path.is_absolute():
            path = REPO_DIR / path
        return str(path)
    return str(REPO_DIR / 'streams.db')
