#!/usr/bin/env python3
"""
Clustering por Lotes - Fase 2
Massive clustering for 19k+ streams
"""
import asyncio
import hashlib
import time
from collections import defaultdict
from runtime.db import Database, Cluster, ClusterStream
from runtime.utils import normalize_channel_name, extract_domain

MIN_CLUSTER_SIZE = 2


async def cluster_by_name(db: Database) -> dict:
    print("[ClusterBatch] Fase A: clustering by channel name...")
    
    cursor = db.conn.cursor()
    
    # Get distinct channels that have enough streams
    cursor.execute("""
        SELECT LOWER(channel) as ch, COUNT(*) as c
        FROM streams
        WHERE channel IS NOT NULL 
        AND channel != '' 
        AND LOWER(channel) NOT LIKE '%chrome%'
        AND LOWER(channel) NOT LIKE '%safari%'
        AND LENGTH(channel) < 40
        GROUP BY LOWER(channel)
    """)
    
    all_groups = cursor.fetchall()
    valid_groups = [(r[0], r[1]) for r in all_groups if r[1] >= MIN_CLUSTER_SIZE]
    
    print(f"[ClusterBatch] Found {len(valid_groups)} groups with >={MIN_CLUSTER_SIZE} streams")
    
    results = {'clusters': 0, 'streams': 0}
    
    for ch_lower, count in valid_groups:
        if results['clusters'] >= 100:
            break  # Limit for testing
        
        cursor.execute("""
            SELECT url FROM streams 
            WHERE LOWER(channel) = ? AND url IS NOT NULL
        """, (ch_lower,))
        
        urls = [r[0] for r in cursor.fetchall()]
        
        if not urls:
            continue
        
        cursor.execute("""
            SELECT channel FROM streams 
            WHERE LOWER(channel) = ? LIMIT 1
        """, (ch_lower,))
        
        orig_row = cursor.fetchone()
        canonical = orig_row[0] if orig_row else ch_lower
        
        cluster_id = hashlib.sha256(ch_lower.encode()).hexdigest()[:12]
        
        cluster = Cluster(
            cluster_id=cluster_id,
            canonical_name=normalize_channel_name(canonical),
            confidence=0.5,
            created_at=int(time.time()),
            updated_at=int(time.time())
        )
        db.insert_cluster(cluster)
        
        for i, url in enumerate(urls[:15]):
            cs = ClusterStream(
                cluster_id=cluster_id,
                stream_url=url,
                priority=1.0 - (i * 0.05),
                is_primary=(i == 0),
                last_check=0
            )
            db.insert_cluster_stream(cs)
        
        results['clusters'] += 1
        results['streams'] += len(urls[:15])
        
        if results['clusters'] % 10 == 0:
            print(f"[ClusterBatch] Progress: {results['clusters']} clusters, {results['streams']} streams...")
    
    print(f"[ClusterBatch] Fase A complete: {results}")
    return results


async def cluster_by_domain(db: Database) -> dict:
    print("[ClusterBatch] Fase B: clustering unclustered by domain...")
    
    cursor = db.conn.cursor()
    
    cursor.execute("""
        SELECT url, channel FROM streams 
        WHERE url NOT IN (SELECT stream_url FROM cluster_streams)
        AND url IS NOT NULL AND url != ''
        AND channel IS NOT NULL AND channel != ''
        LIMIT 2000
    """)
    
    url_channel = [(r[0], r[1]) for r in cursor.fetchall()]
    
    results = {'clusters': 0, 'streams': 0}
    
    domain_map = defaultdict(list)
    for url, ch in url_channel:
        domain = extract_domain(url)
        domain_map[domain].append((url, ch))
    
    for domain, items in domain_map.items():
        if len(items) < MIN_CLUSTER_SIZE:
            continue
        
        if results['clusters'] >= 50:
            break
        
        canonical = f"domain_{domain[:30]}"
        cluster_id = hashlib.sha256(domain.encode()).hexdigest()[:12]
        
        cluster = Cluster(
            cluster_id=cluster_id,
            canonical_name=canonical,
            confidence=0.3,
            created_at=int(time.time()),
            updated_at=int(time.time())
        )
        db.insert_cluster(cluster)
        
        for i, (url, ch) in enumerate(items[:10]):
            cs = ClusterStream(
                cluster_id=cluster_id,
                stream_url=url,
                priority=0.5,
                is_primary=(i == 0),
                last_check=0
            )
            db.insert_cluster_stream(cs)
        
        results['clusters'] += 1
        results['streams'] += len(items[:10])
    
    print(f"[ClusterBatch] Fase B complete: {results}")
    return results


async def run_full_clustering(db: Database = None) -> dict:
    db = db or Database()
    
    print("[ClusterBatch] Starting clustering pipeline...")
    
    results_a = await cluster_by_name(db)
    results_b = await cluster_by_domain(db)
    
    cursor = db.conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM clusters")
    total_clusters = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM cluster_streams")
    total_streams = cursor.fetchone()[0]
    
    print(f"[ClusterBatch] FINAL: {total_clusters} clusters, {total_streams} clustered streams")
    
    return {'clusters': total_clusters, 'cluster_streams': total_streams}


async def main():
    db = Database()
    await run_full_clustering(db)

if __name__ == '__main__':
    asyncio.run(main())