#!/usr/bin/env python3
"""
Level Manager - Fase 3
Sistema de niveles para control de recursos
"""
import time
from typing import Optional

from runtime.db import Database, Cluster


LEVELS = ['cold', 'warm', 'hot', 'active']

LEVEL thresholds = {
    'cold': 0,
    'warm': 10,
    'hot': 50,
    'active': 100
}


class LevelManager:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
    
    def get_cluster_level(self, cluster_id: str) -> str:
        cursor = self.db.conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM fusion_state 
            WHERE cluster_id = ? AND last_switch > ?
        """, (cluster_id, int(time.time()) - 3600))
        
        switches_1h = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM cluster_streams cs
            JOIN streams s ON s.url = cs.stream_url
            WHERE cs.cluster_id = ? AND s.last_check > ?
        """, (cluster_id, int(time.time()) - 3600))
        
        active_streams = cursor.fetchone()[0]
        
        usage_score = switches_1h * 10 + active_streams
        
        if usage_score >= LEVELS['active']:
            return 'active'
        elif usage_score >= LEVELS['hot']:
            return 'hot'
        elif usage_score >= LEVELS['warm']:
            return 'warm'
        else:
            return 'cold'
    
    def get_clusters_by_level(self, level: str) -> list[Cluster]:
        cursor = self.db.conn.cursor()
        
        if level == 'cold':
            cursor.execute("""
                SELECT c.* FROM clusters c
                LEFT JOIN fusion_state f ON f.cluster_id = c.cluster_id
                WHERE f.cluster_id IS NULL OR f.switch_count < 5
            """)
        elif level == 'warm':
            cursor.execute("""
                SELECT c.* FROM clusters c
                JOIN fusion_state f ON f.cluster_id = c.cluster_id
                WHERE f.switch_count BETWEEN 5 AND 20
            """)
        elif level == 'hot':
            cursor.execute("""
                SELECT c.* FROM clusters c
                JOIN fusion_state f ON f.cluster_id = c.cluster_id
                WHERE f.switch_count > 20
            """)
        elif level == 'active':
            cursor.execute("""
                SELECT c.* FROM clusters c
                JOIN fusion_state f ON f.cluster_id = c.cluster_id
                WHERE f.last_switch > ?
            """, (int(time.time()) - 300))
        else:
            return []
        
        return [Cluster(**dict(row)) for row in cursor.fetchall()]
    
    def update_all_levels(self) -> dict:
        clusters = self.db.get_all_clusters()
        
        stats = {'cold': 0, 'warm': 0, 'hot': 0, 'active': 0}
        
        for cluster in clusters:
            level = self.get_cluster_level(cluster.cluster_id)
            stats[level] += 1
        
        print(f"[LevelManager] Distribution: {stats}")
        return stats
    
    def get_prioritized_clusters(self, max_active: int = 50) -> list[tuple[str, str]]:
        cursor = self.db.conn.cursor()
        
        cursor.execute("""
            SELECT c.cluster_id, 
                   COALESCE(f.switch_count, 0) as switches,
                   (SELECT COUNT(*) FROM cluster_streams WHERE cluster_id = c.cluster_id) as stream_count
            FROM clusters c
            LEFT JOIN fusion_state f ON f.cluster_id = c.cluster_id
            ORDER BY switches DESC, stream_count DESC
            LIMIT ?
        """, (max_active,))
        
        results = []
        for row in cursor.fetchall():
            level = self.get_cluster_level(row[0])
            results.append((row[0], level))
        
        return results
    
    def get_analysis_priority(self) -> list[tuple[str, str]]:
        priority = []
        
        for level in ['active', 'hot', 'warm', 'cold']:
            clusters = self.get_clusters_by_level(level)
            priority.extend([(c.cluster_id, level) for c in clusters])
        
        return priority[:100]


async def main():
    import sys
    
    manager = LevelManager()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--update':
            manager.update_all_levels()
        elif sys.argv[1] == '--priority':
            clusters = manager.get_prioritized_clusters()
            print(f"\n[Priority] Top {len(clusters)}:")
            for cid, level in clusters[:20]:
                print(f"  {cid}: {level}")
        elif sys.argv[1] == '--analysis':
            clusters = manager.get_analysis_priority()
            print(f"\n[Analysis] {len(clusters)} clusters by priority")
    else:
        stats = manager.update_all_levels()


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())