import sqlite3
import os

DB_PATH = os.environ.get('DB_PATH', 'streams.db')

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS streams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE,
    channel TEXT,
    country TEXT DEFAULT 'UNKNOWN',
    status TEXT DEFAULT 'unknown',
    latency REAL DEFAULT 999,
    failures INTEGER DEFAULT 0,
    last_check INTEGER DEFAULT 0,
    score REAL DEFAULT 0
)
""")

cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_channel ON streams(channel)
""")

cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_status ON streams(status)
""")

conn.commit()

def get_connection():
    return conn