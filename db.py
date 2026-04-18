import sqlite3
import os
from pathlib import Path

DATA_DIR = Path(__file__).parent / 'data' / 'normalized'
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = str(DATA_DIR / 'streams.db')


def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    from models import ALL_SCHEMAS, SCHEMA_INDEXES
    
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    for schema in ALL_SCHEMAS:
        cursor.executescript(schema)
    
    for idx in SCHEMA_INDEXES.split(';'):
        if idx.strip():
            cursor.execute(idx.strip())
    
    conn.commit()
    return conn


conn = init_db()


def get_db_path():
    return DB_PATH