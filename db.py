import sqlite3
import os
from models import SCHEMA_STREAMS, SCHEMA_NODES, SCHEMA_INDEXES

DB_PATH = os.environ.get('DB_PATH', 'streams.db')

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

for schema in [SCHEMA_STREAMS, SCHEMA_NODES]:
    cursor.execute(schema)

for idx in SCHEMA_INDEXES.split(';'):
    if idx.strip():
        cursor.execute(idx.strip())

conn.commit()

def get_connection():
    return conn