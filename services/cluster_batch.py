#!/usr/bin/env python3
"""
Clustering por Lotes - Fase 2
Massive clustering for 19k+ streams
"""
import asyncio
import hashlib
import time
import json
from typing import Optional
from collections import defaultdict
from urllib.parse import urlparse

from runtime.db import Database, Cluster, ClusterStream
from runtime.utils import normalize_channel_name, extract_domain, extract_base_path, detect_stream_type, string_similarity


BATCH_SIZE = 2000
MIN_CLUSTER_SIZE = 2


async def cluster_by_name(db: Database) -> dict:
    print("[ClusterBatch] Fase A: pre-cluster by name...")
    
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT channel, COUNT(*) as c, GROUP_CONCAT(url) as urls
        FROM streams 
        WHERE status IN ('cold', 'warm', 'online')
        GROUP BY channel
        HAVING c >= ?
    """, (MIN_CLUSTER_SIZE,))
    
    rows = cursor.fetchall()
    print(f"[ClusterBatch] Found {len(rows)} name groups")
    
    results = {'clusters': 0, 'streams': 0}
    
    for row in rows:
        channel = row[0]
        urls = row[2].split(',') if row[2] else []
        
        if not channel or not urls:
            continue
        
        cluster_id = hashlib.sha256(channel.encode()).hexdigest()[:12]
        
        cluster = Cluster(
            cluster_id=cluster_id,
            canonical_name=normalize_channel_name(channel),
            confidence=0.5,
            created_at=int(time.time()),
            updated_at=int(time.time())
        )
        
        db.insert_cluster(cluster)
        
        for i, url in enumerate(urls[:20]):
            cs = ClusterStream(
                cluster_id=cluster_id,
                stream_url=url,
                priority=1.0 - (i * 0.05),
                is_primary=(i == 0),
                last_check=0
            )
            db.insert_cluster_stream(cs)
        
        results['clusters'] += 1
        results['streams'] += len(urls[:20])
        
        if results['clusters'] % 100 == 0:
            print(f"[ClusterBatch] Processed {results['clusters']} groups...")
    
    print(f"[ClusterBatch] Fase A complete: {results}")
    return results


async def cluster_by_domain(db: Database) -> dict:
    print("[ClusterBatch] Fase B: refinement by domain...")
    
    cursor = db.conn.cursor()
    cursor.execute("SELECT DISTINCT channel FROM streams WHERE channel IS NOT NULL")
    channels = [row[0] for row in cursor.fetchall()]
    
    results = {'merged': 0, 'streams': 0}
    
    for channel in channels:
        if not channel:
            continue
        
        cursor.execute("""
            SELECT url FROM streams 
            WHERE channel = ? AND status IN ('cold', 'warm', 'online')
        """, (channel,))
        
        urls = [row[0] for row in cursor.fetchall()]
        
        if len(urls) < 2:
            continue
        
        domain_groups = defaultdict(list)
        
        for url in urls:
            domain = extract_domain(url)
            domain_groups[domain].append(url)
        
        for domain, domain_urls in domain_groups.items():
            if len(domain_urls) < MIN_CLUSTER_SIZE:
                continue
            
            cluster_id = hashlib.sha256(f"{channel}:{domain}".encode()).hexdigest()[:12]
            
            existing = db.get_cluster(cluster_id)
            if existing:
                for url in domain_urls:
                    cs = ClusterStream(
                        cluster_id=cluster_id,
                        stream_url=url,
                        priority=0.7,
                        is_primary=False,
                        last_check=0
                    )
                    db.insert_cluster_stream(cs)
                    results['streams'] += 1
            else:
                cluster = Cluster(
                    cluster_id=cluster_id,
                    canonical_name=normalize_channel_name(channel),
                    confidence=0.6,
                    created_at=int(time.time()),
                    updated_at=int(time.time())
                )
                
                db.insert_cluster(cluster)
                
                for i, url in enumerate(domain_urls):
                    cs = ClusterStream(
                        cluster_id=cluster_id,
                        stream_url=url,
                        priority=1.0 - (i * 0.05),
                        is_primary=(i == 0),
                        last_check=0
                    )
                    db.insert_cluster_stream(cs)
                    results['streams'] += 1
                
                results['merged'] += 1
    
    print(f"[ClusterBatch] Fase B complete: {results}")
    return results


async def cluster_by_path(db: Database) -> dict:
    print("[ClusterBatch] Fase C: refinement by path pattern...")
    
    cursor = db.conn.cursor()
    cursor.execute("SELECT cluster_id FROM clusters")
    clusters = [row[0] for row in cursor.fetchall()]
    
    results = {'refined': 0}
    
    for cluster_id in clusters[:500]:
        cursor.execute("""
            SELECT stream_url FROM cluster_streams 
            WHERE cluster_id = ?
        """, (cluster_id,))
        
        urls = [row[0] for row in cursor.fetchall()]
        
        if len(urls) < 3:
            continue
        
        path_groups = defaultdict(list)
        
        for url in urls:
            try:
                base = extract_base_path(url)
                path_groups[base].append(url)
            except:
                path_groups['default'].append(url)
        
        if len(path_groups) < 2:
            continue
        
        paths = sorted(path_groups.keys(), key=lambda x: len(path_groups[x]), reverse=True)
        
        primary_paths = set(paths[:2])
        
        for path, path_urls in path_groups.items():
            if path in primary_paths:
                for url in path_urls:
                    cursor.execute("""
                        UPDATE cluster_streams 
                        SET priority = priority + 0.1
                        WHERE cluster_id = ? AND stream_url = ?
                    """, (cluster_id, url))
        
        results['refined'] += 1
    
    db.conn.commit()
    print(f"[ClusterBatch] Fase C complete: {results}")
    return results


async def run_full_clustering(db: Database = None) -> dict:
    db = db or Database()
    
    print("[ClusterBatch] Starting full clustering pipeline...")
    
    results = await cluster_by_name(db)
    results = await cluster_by_domain(db)
    results = await cluster_by_path(db)
    
    cursor = db.conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM clusters")
    total_clusters = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM cluster_streams")
    total_streams = cursor.fetchone()[0]
    
    print(f"[ClusterBatch] FINAL: {total_clusters} clusters, {total_streams} streams in clusters")
    
    return {
        'clusters': total_clusters,
        'cluster_streams': total_streams
    }


async def main():
    import sys
    
    db = Database()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--name':
            await cluster_by_name(db)
        elif sys.argv[1] == '--domain':
            await cluster_by_domain(db)
        elif sys.argv[1] == '--path':
            await cluster_by_path(db)
        else:
            await run_full_clustering(db)
    else:
        cursor = db.conn.cursor()
        cursor.execute("SELECT status, COUNT(*) FROM streams GROUP BY status")
        print("\n[DB State]:")
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]}")
        
        cursor.execute("SELECT COUNT(*) FROM clusters")
        print(f"\n[Clusters]: {cursor.fetchone()[0]}")


if __name__ == '__main__':
    asyncio.run(main())