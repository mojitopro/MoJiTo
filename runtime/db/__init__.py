import sqlite3
import json
import time
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict


ROOT = Path(__file__).parent.parent.parent
DB_PATH = str(ROOT / 'data' / 'normalized' / 'streams.db')


@dataclass
class StreamRecord:
    url: str
    channel: Optional[str] = None
    country: str = 'UNKNOWN'
    status: str = 'unknown'
    latency: float = 999
    failures: int = 0
    last_check: int = 0
    score: float = 0
    node_ip: Optional[str] = None


@dataclass
class StreamMetrics:
    stream_url: str
    startup_time: float = 0
    freeze_count: int = 0
    freeze_duration: float = 0
    avg_frame_delta: float = 0
    black_ratio: float = 0
    motion_score: float = 0
    stability: float = 0
    last_check: int = 0


@dataclass
class Cluster:
    cluster_id: str
    canonical_name: str
    confidence: float = 0
    created_at: int = 0
    updated_at: int = 0


@dataclass
class ClusterStream:
    cluster_id: str
    stream_url: str
    priority: float = 0
    is_primary: bool = False
    last_check: int = 0


@dataclass
class FusionState:
    cluster_id: str
    active_stream: Optional[str] = None
    backup_streams: str = '[]'
    switch_count: int = 0
    last_switch: int = 0
    buffer_ms: int = 0


class Database:
    def __init__(self, path: str = None):
        self.path = path or DB_PATH
        if path is None:
            path = DB_PATH
        
        # Use existing DB if it exists
        if not Path(self.path).exists():
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='streams'")
        if cursor.fetchone():
            return  # Tables exist
        
        self._init_tables()
    
    def _init_tables(self):
        cursor = self.conn.cursor()
        
        cursor.execute("""
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
        """)
        
        cursor.execute("""
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
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clusters (
                cluster_id TEXT PRIMARY KEY,
                canonical_name TEXT,
                confidence REAL DEFAULT 0,
                created_at INTEGER DEFAULT (strftime('%s', 'now')),
                updated_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cluster_streams (
                cluster_id TEXT,
                stream_url TEXT,
                priority REAL DEFAULT 0,
                is_primary INTEGER DEFAULT 0,
                last_check INTEGER DEFAULT 0,
                FOREIGN KEY (cluster_id) REFERENCES clusters(cluster_id),
                UNIQUE(cluster_id, stream_url)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fusion_state (
                cluster_id TEXT PRIMARY KEY,
                active_stream TEXT,
                backup_streams TEXT DEFAULT '[]',
                switch_count INTEGER DEFAULT 0,
                last_switch INTEGER DEFAULT 0,
                buffer_ms INTEGER DEFAULT 0,
                created_at INTEGER DEFAULT (strftime('%s', 'now')),
                updated_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_streams_channel ON streams(channel)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_streams_status ON streams(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stream_metrics_last_check ON stream_metrics(last_check)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_clusters_canonical ON clusters(canonical_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cluster_streams_cluster ON cluster_streams(cluster_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fusion_state_cluster ON fusion_state(cluster_id)")
        
        self.conn.commit()
    
    def insert_stream(self, record: StreamRecord) -> bool:
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO streams 
                (url, channel, country, status, latency, failures, last_check, score, node_ip)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (record.url, record.channel, record.country, record.status,
                  record.latency, record.failures, record.last_check, record.score, record.node_ip))
            self.conn.commit()
            return True
        except:
            return False
    
    def insert_stream_batch(self, records: list[StreamRecord]) -> int:
        cursor = self.conn.cursor()
        count = 0
        for record in records:
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO streams 
                    (url, channel, country, status, latency, failures, last_check, score, node_ip)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (record.url, record.channel, record.country, record.status,
                      record.latency, record.failures, record.last_check, record.score, record.node_ip))
                count += 1
            except:
                pass
        self.conn.commit()
        return count
    
    def get_stream(self, url: str) -> Optional[StreamRecord]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM streams WHERE url = ?", (url,))
        row = cursor.fetchone()
        if row:
            return StreamRecord(**dict(row))
        return None
    
    def get_all_streams(self, status: str = None) -> list[StreamRecord]:
        cursor = self.conn.cursor()
        if status:
            cursor.execute("SELECT * FROM streams WHERE status = ?", (status,))
        else:
            cursor.execute("SELECT * FROM streams")
        return [StreamRecord(**dict(row)) for row in cursor.fetchall()]
    
    def update_stream_status(self, url: str, status: str, latency: float = 999) -> None:
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE streams SET status = ?, latency = ?, last_check = ? WHERE url = ?
        """, (status, latency, int(time.time()), url))
        self.conn.commit()
    
    def insert_stream_metrics(self, metrics: StreamMetrics) -> bool:
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO stream_metrics 
                (stream_url, startup_time, freeze_count, freeze_duration, avg_frame_delta,
                 black_ratio, motion_score, stability, last_check)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (metrics.stream_url, metrics.startup_time, metrics.freeze_count, metrics.freeze_duration,
                  metrics.avg_frame_delta, metrics.black_ratio, metrics.motion_score, metrics.stability,
                  metrics.last_check))
            self.conn.commit()
            return True
        except:
            return False
    
    def get_stream_metrics(self, url: str) -> Optional[StreamMetrics]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM stream_metrics WHERE stream_url = ?", (url,))
        row = cursor.fetchone()
        if row:
            return StreamMetrics(**dict(row))
        return None
    
    def get_all_stream_metrics(self) -> list[StreamMetrics]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM stream_metrics")
        return [StreamMetrics(**dict(row)) for row in cursor.fetchall()]
    
    def insert_cluster(self, cluster: Cluster) -> bool:
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO clusters (cluster_id, canonical_name, confidence, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (cluster.cluster_id, cluster.canonical_name, cluster.confidence,
                  cluster.created_at, cluster.updated_at))
            self.conn.commit()
            return True
        except:
            return False
    
    def insert_cluster_stream(self, cs: ClusterStream) -> bool:
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO cluster_streams 
                (cluster_id, stream_url, priority, is_primary, last_check)
                VALUES (?, ?, ?, ?, ?)
            """, (cs.cluster_id, cs.stream_url, cs.priority, int(cs.is_primary), cs.last_check))
            self.conn.commit()
            return True
        except:
            return False
    
    def get_cluster(self, cluster_id: str) -> Optional[Cluster]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM clusters WHERE cluster_id = ?", (cluster_id,))
        row = cursor.fetchone()
        if row:
            return Cluster(**dict(row))
        return None
    
    def get_cluster_streams(self, cluster_id: str) -> list[ClusterStream]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM cluster_streams WHERE cluster_id = ? ORDER BY priority DESC", (cluster_id,))
        result = []
        for row in cursor.fetchall():
            d = dict(row)
            d['is_primary'] = bool(d.get('is_primary', 0))
            result.append(ClusterStream(**d))
        return result
    
    def get_all_clusters(self) -> list[Cluster]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM clusters")
        return [Cluster(**dict(row)) for row in cursor.fetchall()]
    
    def insert_fusion_state(self, state: FusionState) -> bool:
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO fusion_state 
                (cluster_id, active_stream, backup_streams, switch_count, last_switch, buffer_ms, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (state.cluster_id, state.active_stream, state.backup_streams, state.switch_count,
                  state.last_switch, state.buffer_ms))
            self.conn.commit()
            return True
        except:
            return False
    
    def get_fusion_state(self, cluster_id: str) -> Optional[FusionState]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM fusion_state WHERE cluster_id = ?", (cluster_id,))
        row = cursor.fetchone()
        if row:
            return FusionState(**dict(row))
        return None
    
    def update_fusion_active(self, cluster_id: str, active_stream: str) -> None:
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE fusion_state 
            SET active_stream = ?, switch_count = switch_count + 1, last_switch = ?, updated_at = ?
            WHERE cluster_id = ?
        """, (active_stream, int(time.time()), int(time.time()), cluster_id))
        self.conn.commit()
    
    def get_stats(self) -> dict:
        cursor = self.conn.cursor()
        stats = {}
        
        cursor.execute("SELECT COUNT(*) as c FROM streams")
        stats['streams'] = cursor.fetchone()['c']
        
        cursor.execute("SELECT COUNT(*) as c FROM stream_metrics")
        stats['metrics'] = cursor.fetchone()['c']
        
        cursor.execute("SELECT COUNT(*) as c FROM clusters")
        stats['clusters'] = cursor.fetchone()['c']
        
        cursor.execute("SELECT COUNT(*) as c FROM fusion_state")
        stats['fusion_states'] = cursor.fetchone()['c']
        
        return stats


db = Database()