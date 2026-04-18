#!/usr/bin/env python3
"""
Scanner Service
Continuous stream ingestion and validation
"""
import asyncio
import aiohttp
import time
import json
from typing import Optional
from urllib.parse import urlparse

from runtime.db import Database, StreamRecord


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (SMART-TV) AppleWebKit/537.36',
    'Accept': '*/*',
    'Connection': 'keep-alive',
}


class ScannerService:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
        self.session: Optional[aiohttp.ClientSession] = None
        self.running = False
    
    async def start(self):
        self.session = aiohttp.ClientSession()
        self.running = True
        print("[Scanner] Started")
    
    async def stop(self):
        self.running = False
        if self.session:
            await self.session.close()
        print("[Scanner] Stopped")
    
    async def ingest_m3u(self, m3u_path: str) -> int:
        count = 0
        try:
            with open(m3u_path, 'r') as f:
                content = f.read()
            
            lines = content.splitlines()
            current_name = None
            current_attrs = {}
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith('#EXTINF:'):
                    current_attrs = self._parse_extinf(line)
                    current_name = current_attrs.get('name', 'Unknown')
                
                elif line.startswith('http') and current_name:
                    url = line
                    if self._is_valid_url(url):
                        record = StreamRecord(
                            url=url,
                            channel=current_name,
                            status='pending',
                            last_check=int(time.time())
                        )
                        if self.db.insert_stream(record):
                            count += 1
                    current_name = None
            
            print(f"[Scanner] Ingested {count} streams from {m3u_path}")
        except Exception as e:
            print(f"[Scanner] Error: {e}")
        
        return count
    
    async def ingest_json(self, json_path: str) -> int:
        count = 0
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            channels = data.get('channels', [])
            for ch in channels:
                name = ch.get('name', 'Unknown')
                urls = ch.get('urls', []) or ch.get('streams', [])
                
                for url in urls:
                    if isinstance(url, dict):
                        url = url.get('url', '')
                    
                    if url and self._is_valid_url(url):
                        record = StreamRecord(
                            url=url,
                            channel=name,
                            status='pending',
                            last_check=int(time.time())
                        )
                        if self.db.insert_stream(record):
                            count += 1
            
            print(f"[Scanner] Ingested {count} streams from {json_path}")
        except Exception as e:
            print(f"[Scanner] Error: {e}")
        
        return count
    
    async def validate_stream(self, url: str, timeout: float = 5.0) -> dict:
        result = {
            'url': url,
            'valid': False,
            'status': 'unknown',
            'latency': 999,
            'content_type': '',
            'size': 0
        }
        
        if not self.session:
            return result
        
        try:
            start = time.time()
            timeout_obj = aiohttp.ClientTimeout(total=timeout)
            
            async with self.session.head(url, headers=HEADERS, timeout=timeout_obj) as resp:
                result['latency'] = (time.time() - start) * 1000
                result['status'] = resp.status
                result['content_type'] = resp.headers.get('Content-Type', '')
                
                if resp.status in [200, 206]:
                    result['valid'] = True
                    self.db.update_stream_status(url, 'online', result['latency'])
                else:
                    self.db.update_stream_status(url, 'offline', result['latency'])
        
        except asyncio.TimeoutError:
            result['status'] = 'timeout'
            self.db.update_stream_status(url, 'timeout', 999)
        except Exception as e:
            result['status'] = str(e)[:30]
            self.db.update_stream_status(url, 'error', 999)
        
        return result
    
    async def scan_all(self, batch_size: int = 50) -> dict:
        streams = self.db.get_all_streams(status='pending')
        results = {'tested': 0, 'online': 0, 'offline': 0}
        
        for i, stream in enumerate(streams[:batch_size]):
            result = await self.validate_stream(stream.url)
            results['tested'] += 1
            
            if result['valid']:
                results['online'] += 1
            else:
                results['offline'] += 1
            
            if (i + 1) % 10 == 0:
                print(f"[Scanner] Tested {i+1}/{min(batch_size, len(streams))}...")
        
        return results
    
    def _parse_extinf(self, line: str) -> dict:
        attrs = {'name': ''}
        
        name_match = __import__('re').search(r'#EXTINF:[^,]*,(.+)', line)
        if name_match:
            attrs['name'] = name_match.group(1).strip()
        
        tvg_id = __import__('re').search(r'tvg-id="([^"]*)"', line)
        if tvg_id:
            attrs['tvg_id'] = tvg_id.group(1)
        
        tvg_name = __import__('re').search(r'tvg-name="([^"]*)"', line)
        if tvg_name:
            attrs['tvg_name'] = tvg_name.group(1)
        
        group = __import__('re').search(r'group-title="([^"]*)"', line)
        if group:
            attrs['group'] = group.group(1)
        
        return attrs
    
    def _is_valid_url(self, url: str) -> bool:
        if not url:
            return False
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme in ['http', 'https'] and parsed.netloc)
        except:
            return False


async def main():
    import sys
    
    scanner = ScannerService()
    await scanner.start()
    
    if len(sys.argv) > 1:
        path = sys.argv[1]
        if path.endswith('.m3u'):
            await scanner.ingest_m3u(path)
        elif path.endswith('.json'):
            await scanner.ingest_json(path)
    
    await scanner.scan_all()
    await scanner.stop()
    
    stats = scanner.db.get_stats()
    print(f"\n[Scanner] Stats: {stats}")


if __name__ == '__main__':
    asyncio.run(main())