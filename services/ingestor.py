#!/usr/bin/env python3
"""
Bulk Ingest Service
Massive stream ingestion with pre-filter for 19k+ streams
"""
import asyncio
import aiohttp
import time
import json
import re
from typing import Optional
from urllib.parse import urlparse
from collections import defaultdict

from runtime.db import Database, StreamRecord
from runtime.utils import is_valid_url, normalize_channel_name, detect_stream_type


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (SMART-TV) AppleWebKit/537.36',
    'Accept': '*/*',
    'Connection': 'keep-alive',
}

VALID_EXTENSIONS = {'.m3u8', '.ts', '.mp4', '.mkv'}
VALID_SCHEMES = {'http', 'https'}


class BulkIngest:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
        self.session: Optional[aiohttp.ClientSession] = None
        self.stats = {
            'input': 0,
            'valid': 0,
            'invalid': 0,
            'duplicates': 0,
            'inserted': 0
        }
    
    async def start(self):
        self.session = aiohttp.ClientSession()
        print("[BulkIngest] Started")
    
    async def stop(self):
        if self.session:
            await self.session.close()
        print("[BulkIngest] Stopped")
    
    def pre_filter_url(self, url: str) -> tuple[bool, str]:
        if not url or len(url) < 10:
            return False, 'too_short'
        
        if not url.startswith(('http://', 'https://')):
            return False, 'no_scheme'
        
        try:
            parsed = urlparse(url)
            if parsed.scheme not in VALID_SCHEMES:
                return False, 'invalid_scheme'
            if not parsed.netloc:
                return False, 'no_domain'
            
            path = parsed.path.lower()
            if any(path.endswith(ext) for ext in VALID_EXTENSIONS):
                return True, 'valid'
            
            if '.m3u' in path or 'playlist' in path:
                return True, 'valid'
            
            return False, 'no_valid_ext'
        except:
            return False, 'parse_error'
    
    def extract_streams_from_m3u(self, content: str) -> list[tuple[str, str]]:
        streams = []
        lines = content.splitlines()
        current_name = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('#EXTINF:'):
                match = re.search(r',(.+)', line)
                if match:
                    current_name = match.group(1).strip()
            
            elif line.startswith('http'):
                valid, reason = self.pre_filter_url(line)
                if valid:
                    streams.append((line, current_name or 'Unknown'))
        
        return streams
    
    def extract_from_json(self, data: dict) -> list[tuple[str, str]]:
        streams = []
        
        channels = data.get('channels', [])
        for ch in channels:
            name = ch.get('name', 'Unknown')
            urls = ch.get('urls', []) or ch.get('streams', []) or ch.get('url', [])
            
            if isinstance(urls, str):
                urls = [urls]
            
            for url in urls:
                if isinstance(url, dict):
                    url = url.get('url', '')
                if url:
                    valid, _ = self.pre_filter_url(url)
                    if valid:
                        streams.append((url, name))
        
        return streams
    
    async def ingest_m3u_file(self, path: str) -> dict:
        self.stats['input'] = 0
        self.stats['valid'] = 0
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            streams = self.extract_streams_from_m3u(content)
            self.stats['input'] = len(streams)
            
            return await self._insert_streams_batch(streams)
        
        except Exception as e:
            print(f"[BulkIngest] Error reading {path}: {e}")
            return self.stats
    
    async def ingest_json_file(self, path: str) -> dict:
        self.stats['input'] = 0
        self.stats['valid'] = 0
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            streams = self.extract_from_json(data)
            self.stats['input'] = len(streams)
            
            return await self._insert_streams_batch(streams)
        
        except Exception as e:
            print(f"[BulkIngest] Error reading {path}: {e}")
            return self.stats
    
    async def ingest_directory(self, directory: str, patterns: list[str] = None) -> dict:
        patterns = patterns or ['*.m3u', '*.json']
        
        import glob
        all_files = []
        
        for pattern in patterns:
            all_files.extend(glob.glob(f"{directory}/{pattern}"))
        
        all_files = list(set(all_files))
        
        print(f"[BulkIngest] Found {len(all_files)} files")
        
        for filepath in all_files:
            if filepath.endswith('.m3u'):
                await self.ingest_m3u_file(filepath)
            elif filepath.endswith('.json'):
                await self.ingest_json_file(filepath)
        
        return self.stats
    
    async def _insert_streams_batch(self, streams: list[tuple[str, str]], batch_size: int = 500) -> dict:
        existing = set()
        
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT url FROM streams")
        for row in cursor.fetchall():
            existing.add(row[0])
        
        to_insert = []
        
        for url, name in streams:
            if url in existing:
                self.stats['duplicates'] += 1
                continue
            
            valid, _ = self.pre_filter_url(url)
            if not valid:
                self.stats['invalid'] += 1
                continue
            
            stream_type = detect_stream_type(url)
            
            record = StreamRecord(
                url=url,
                channel=normalize_channel_name(name),
                status='cold',
                last_check=0,
                node_ip=self._extract_ip(url)
            )
            
            to_insert.append(record)
            existing.add(url)
            self.stats['valid'] += 1
            
            if len(to_insert) >= batch_size:
                count = self.db.insert_stream_batch(to_insert)
                self.stats['inserted'] += count
                to_insert = []
                print(f"[BulkIngest] Inserted {self.stats['inserted']}...")
        
        if to_insert:
            count = self.db.insert_stream_batch(to_insert)
            self.stats['inserted'] += count
        
        return self.stats
    
    def _extract_ip(self, url: str) -> Optional[str]:
        try:
            parsed = urlparse(url)
            netloc = parsed.netloc
            
            if ':' in netloc:
                netloc = netloc.split(':')[0]
            
            parts = netloc.split('.')
            if len(parts) == 4 and all(p.isdigit() for p in parts):
                return netloc
            return None
        except:
            return None
    
    async def light_test_batch(self, urls: list[str], timeout: float = 3.0, batch_size: int = 50) -> dict:
        if not self.session:
            return {'tested': 0, 'online': 0, 'offline': 0}
        
        results = {'tested': 0, 'online': 0, 'offline': 0}
        
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i+batch_size]
            
            tasks = []
            for url in batch:
                task = asyncio.create_task(self._test_single_url(url, timeout))
                tasks.append(task)
            
            outcomes = await asyncio.gather(*tasks, return_exceptions=True)
            
            for url, result in zip(batch, outcomes):
                results['tested'] += 1
                if isinstance(result, dict) and result.get('online'):
                    results['online'] += 1
                    self.db.update_stream_status(url, 'warm', result.get('latency', 999))
                else:
                    results['offline'] += 1
                    self.db.update_stream_status(url, 'cold', 999)
            
            if (i + batch_size) % 200 == 0:
                print(f"[BulkIngest] Tested {results['tested']}/{len(urls)}...")
        
        return results
    
    async def _test_single_url(self, url: str, timeout: float = 3.0) -> dict:
        result = {'url': url, 'online': False, 'latency': 999}
        
        try:
            start = time.time()
            timeout_obj = aiohttp.ClientTimeout(total=timeout)
            
            async with self.session.head(url, headers=HEADERS, timeout=timeout_obj) as resp:
                result['latency'] = (time.time() - start) * 1000
                result['online'] = resp.status in [200, 206]
                result['status'] = resp.status
        
        except asyncio.TimeoutError:
            result['error'] = 'timeout'
        except Exception as e:
            result['error'] = str(e)[:20]
        
        return result
    
    def get_stats(self) -> dict:
        return self.stats.copy()


async def main():
    import sys
    import glob
    
    ingest = BulkIngest()
    await ingest.start()
    
    if len(sys.argv) > 1:
        path = sys.argv[1]
        
        if path == '--dir' and len(sys.argv) > 2:
            await ingest.ingest_directory(sys.argv[2])
        elif path.endswith('.m3u'):
            await ingest.ingest_m3u_file(path)
        elif path.endswith('.json'):
            await ingest.ingest_json_file(path)
        else:
            print(f"Usage: {sys.argv[0]} <file.m3u|file.json|--dir directory>")
    else:
        db = Database()
        cursor = db.conn.cursor()
        cursor.execute("SELECT COUNT(*), status FROM streams GROUP BY status")
        print("\n[Current DB State]:")
        for row in cursor.fetchall():
            print(f"  {row[1]}: {row[0]}")
    
    print(f"\n[BulkIngest] Final stats: {ingest.get_stats()}")
    
    await ingest.stop()


if __name__ == '__main__':
    asyncio.run(main())