SCHEMA_STREAMS = """
CREATE TABLE IF NOT EXISTS streams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE,
    channel TEXT,
    country TEXT DEFAULT 'UNKNOWN',
    status TEXT DEFAULT 'unknown',
    latency REAL DEFAULT 999,
    failures INTEGER DEFAULT 0,
    last_check INTEGER DEFAULT 0,
    score REAL DEFAULT 0,
    node_ip TEXT
)
"""

SCHEMA_NODES = """
CREATE TABLE IF NOT EXISTS nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip TEXT,
    port INTEGER,
    country TEXT,
    isp TEXT,
    cluster TEXT
)
"""

SCHEMA_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_channel ON streams(channel);
CREATE INDEX IF NOT EXISTS idx_status ON streams(status);
CREATE INDEX IF NOT EXISTS idx_node_ip ON streams(node_ip);
"""