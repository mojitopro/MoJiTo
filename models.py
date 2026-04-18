SCHEMA_STREAMS = """
CREATE TABLE IF NOT EXISTS streams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
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

SCHEMA_STREAM_METRICS = """
CREATE TABLE IF NOT EXISTS stream_metrics (
    stream_url TEXT PRIMARY KEY,
    startup_time REAL DEFAULT 0,
    freeze_count INTEGER DEFAULT 0,
    freeze_duration REAL DEFAULT 0,
    avg_frame_delta REAL DEFAULT 0,
    black_ratio REAL DEFAULT 0,
    motion_score REAL DEFAULT 0,
    stability REAL DEFAULT 0,
    last_check INTEGER DEFAULT 0,
    created_at INTEGER DEFAULT (strftime('%s', 'now'))
)
"""

SCHEMA_CLUSTERS = """
CREATE TABLE IF NOT EXISTS clusters (
    cluster_id TEXT PRIMARY KEY,
    canonical_name TEXT,
    confidence REAL DEFAULT 0,
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
)
"""

SCHEMA_CLUSTER_STREAMS = """
CREATE TABLE IF NOT EXISTS cluster_streams (
    cluster_id TEXT,
    stream_url TEXT,
    priority REAL DEFAULT 0,
    is_primary INTEGER DEFAULT 0,
    last_check INTEGER DEFAULT 0,
    FOREIGN KEY (cluster_id) REFERENCES clusters(cluster_id),
    UNIQUE(cluster_id, stream_url)
)
"""

SCHEMA_FUSION_STATE = """
CREATE TABLE IF NOT EXISTS fusion_state (
    cluster_id TEXT PRIMARY KEY,
    active_stream TEXT,
    backup_streams TEXT,
    switch_count INTEGER DEFAULT 0,
    last_switch INTEGER DEFAULT 0,
    buffer_ms INTEGER DEFAULT 0,
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
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
CREATE INDEX IF NOT EXISTS idx_streams_channel ON streams(channel);
CREATE INDEX IF NOT EXISTS idx_streams_status ON streams(status);
CREATE INDEX IF NOT EXISTS idx_streams_node_ip ON streams(node_ip);
CREATE INDEX IF NOT EXISTS idx_stream_metrics_last_check ON stream_metrics(last_check);
CREATE INDEX IF NOT EXISTS idx_clusters_canonical ON clusters(canonical_name);
CREATE INDEX IF NOT EXISTS idx_cluster_streams_cluster ON cluster_streams(cluster_id);
CREATE INDEX IF NOT EXISTS idx_fusion_state_cluster ON fusion_state(cluster_id);
"""

ALL_SCHEMAS = [
    SCHEMA_STREAMS,
    SCHEMA_STREAM_METRICS,
    SCHEMA_CLUSTERS,
    SCHEMA_CLUSTER_STREAMS,
    SCHEMA_FUSION_STATE,
    SCHEMA_NODES
]