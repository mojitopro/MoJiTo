#!/usr/bin/env python3
"""
Ingest Masivo - Fase 1
Bulk stream ingestion with pre-filter for 19k+ streams
"""
import asyncio
import aiohttp
import time
import json
import re
from typing import Optional
from urllib.parse import urlparse

from runtime.db import Database, StreamRecord
from runtime.utils import normalize_channel_name, detect_stream_type


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (SMART-TV) AppleWebKit/537.36',
    'Accept': '*/*',
    'Connection': 'keep-alive',
}

VALID_EXTENSIONS = ['.m3u8', '.ts', '.mp4', '.mkv', '.m3u']


def pre_filter_url(url: str) -> bool:
    if not url or len(url) < 10 or len(url) > 500:
        return False
    if not url.startswith(('http://', 'https://')):
        return False
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return False
        if not parsed.netloc:
            return False
        path = parsed.path.lower()
        if any(path.endswith(ext) for ext in VALID_EXTENSIONS):
            return True
        if '.m3u' in path or 'playlist' in path:
            return True
        return False
    except:
        return False


async def ingest_m3u(path: str, db: Database = None) -> dict:
    stats = {'input': 0, 'valid': 0, 'inserted': 0, 'duplicates': 0}
    db = db or Database()
    
    existing = set()
    cursor = db.conn.cursor()
    cursor.execute("SELECT url FROM streams")
    for row in cursor.fetchall():
        existing.add(row[0])
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.splitlines()
        current_name = None
        batch = []
        BATCH_SIZE = 500
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('#EXTINF:'):
                match = re.search(r',(.+)', line)
                if match:
                    current_name = match.group(1).strip()
            
            elif line.startswith('http'):
                url = line
                stats['input'] += 1
                
                if url in existing:
                    stats['duplicates'] += 1
                    continue
                
                if not pre_filter_url(url):
                    continue
                
                stats['valid'] += 1
                
                record = StreamRecord(
                    url=url,
                    channel=normalize_channel_name(current_name or 'Unknown'),
                    status='cold',
                    last_check=0
                )
                batch.append(record)
                existing.add(url)
                
                if len(batch) >= BATCH_SIZE:
                    count = db.insert_stream_batch(batch)
                    stats['inserted'] += count
                    batch = []
                    print(f"[Ingest] Inserted {stats['inserted']}...")
        
        if batch:
            count = db.insert_stream_batch(batch)
            stats['inserted'] += count
        
        print(f"[Ingest] {path}: {stats}")
    
    except Exception as e:
        print(f"[Ingest] Error: {e}")
    
    return stats


async def ingest_json(path: str, db: Database = None) -> dict:
    stats = {'input': 0, 'valid': 0, 'inserted': 0, 'duplicates': 0}
    db = db or Database()
    
    existing = set()
    cursor = db.conn.cursor()
    cursor.execute("SELECT url FROM streams")
    for row in cursor.fetchall():
        existing.add(row[0])
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        channels = data.get('channels', [])
        batch = []
        BATCH_SIZE = 500
        
        for ch in channels:
            name = ch.get('name', 'Unknown')
            urls = ch.get('urls', []) or ch.get('streams', [])
            
            if isinstance(urls, str):
                urls = [urls]
            
            for url in urls:
                if isinstance(url, dict):
                    url = url.get('url', '')
                if not url:
                    continue
                
                stats['input'] += 1
                
                if url in existing:
                    stats['duplicates'] += 1
                    continue
                
                if not pre_filter_url(url):
                    continue
                
                stats['valid'] += 1
                
                record = StreamRecord(
                    url=url,
                    channel=normalize_channel_name(name),
                    status='cold',
                    last_check=0
                )
                batch.append(record)
                existing.add(url)
                
                if len(batch) >= BATCH_SIZE:
                    count = db.insert_stream_batch(batch)
                    stats['inserted'] += count
                    batch = []
                    print(f"[Ingest] Inserted {stats['inserted']}...")
        
        if batch:
            count = db.insert_stream_batch(batch)
            stats['inserted'] += count
        
        print(f"[Ingest] {path}: {stats}")
    
    except Exception as e:
        print(f"[Ingest] Error: {e}")
    
    return stats


async def ingest_all(directory: str = '.', db: Database = None) -> dict:
    import glob
    db = db or Database()
    
    patterns = ['*.m3u', '*.json']
    files = []
    
    for pattern in patterns:
        files.extend(glob.glob(f"{directory}/{pattern}"))
    
    files = list(set(files))
    print(f"[Ingest] Found {len(files)} files")
    
    total = {'input': 0, 'valid': 0, 'inserted': 0, 'duplicates': 0}
    
    for filepath in sorted(files):
        if filepath.endswith('.m3u'):
            stats = await ingest_m3u(filepath, db)
        elif filepath.endswith('.json'):
            stats = await ingest_json(filepath, db)
        else:
            continue
        
        for k, v in stats.items():
            total[k] += v
    
    print(f"[Ingest] TOTAL: {total}")
    return total


async def main():
    import sys
    
    if len(sys.argv) > 1:
        path = sys.argv[1]
        
        if path == '--all':
            await ingest_all()
        elif path.endswith('.m3u'):
            await ingest_m3u(path)
        elif path.endswith('.json'):
            await ingest_json(path)
    else:
        db = Database()
        cursor = db.conn.cursor()
        cursor.execute("SELECT status, COUNT(*) FROM streams GROUP BY status")
        print("\n[DB State]:")
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]}")


if __name__ == '__main__':
    asyncio.run(main())