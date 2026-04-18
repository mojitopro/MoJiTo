#!/usr/bin/env python3
"""
Análisis Priorizado - Fase 4
Prioritized analysis with concurrency limits
"""
import asyncio
import aiohttp
import time
import hashlib
from typing import Optional

from runtime.db import Database, StreamMetrics
from runtime.utils import calculate_stream_score
from services.level_manager import LevelManager


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (SMART-TV) AppleWebKit/537.36',
    'Accept': '*/*',
}


MAX_WORKERS = 5
MAX_STREAMS_PER_CLUSTER = 5
ANALYSIS_TIMEOUT = 15


class PrioritizedAnalyzer:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
        self.session: Optional[aiohttp.ClientSession] = None
        self.semaphore = asyncio.Semaphore(MAX_WORKERS)
        self.stats = {'analyzed': 0, 'errors': 0, 'online': 0}
    
    async def start(self):
        self.session = aiohttp.ClientSession()
        print(f"[PrioritizedAnalyzer] Started (max workers: {MAX_WORKERS})")
    
    async def stop(self):
        if self.session:
            await self.session.close()
        print(f"[PrioritizedAnalyzer] Stopped")
    
    async def analyze_stream(self, url: str) -> Optional[StreamMetrics]:
        async with self.semaphore:
            return await self._analyze_single(url)
    
    async def _analyze_single(self, url: str) -> Optional[StreamMetrics]:
        metrics = StreamMetrics(
            stream_url=url,
            last_check=int(time.time())
        )
        
        try:
            startup = await self._measure_startup(url)
            if startup:
                metrics.startup_time = startup
            
            if '.m3u8' in url:
                segments = await self._get_segments(url)
                if segments:
                    temporal = await self._analyze_temporal(segments[:3])
                    metrics.freeze_count = temporal.get('freeze_count', 0)
                    metrics.freeze_duration = temporal.get('freeze_duration', 0)
                    metrics.avg_frame_delta = temporal.get('avg_frame_delta', 4.0)
            
            score = calculate_stream_score(
                metrics.startup_time * 1000 if metrics.startup_time else 999,
                metrics.avg_frame_delta,
                metrics.freeze_duration,
                metrics.black_ratio,
                metrics.motion_score,
                metrics.stability
            )
            
            self.db.insert_stream_metrics(metrics)
            self.stats['analyzed'] += 1
        
        except Exception as e:
            self.stats['errors'] += 1
        
        return metrics
    
    async def _measure_startup(self, url: str) -> Optional[float]:
        if not self.session:
            return None
        
        try:
            start = time.time()
            timeout = aiohttp.ClientTimeout(total=10)
            
            async with self.session.get(url, headers=HEADERS, timeout=timeout) as resp:
                if resp.status in [200, 206]:
                    self.stats['online'] += 1
                    return time.time() - start
                return None
        except:
            return None
    
    async def _get_segments(self, m3u8_url: str) -> list[str]:
        if not self.session:
            return []
        
        try:
            async with self.session.get(m3u8_url, headers=HEADERS) as resp:
                if resp.status != 200:
                    return []
                content = await resp.text()
        except:
            return []
        
        base_url = m3u8_url.rsplit('/', 1)[0] + '/'
        segments = []
        
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith('#'):
                if line.startswith('http'):
                    segments.append(line)
                else:
                    segments.append(base_url + line)
        
        return segments[:10]
    
    async def _analyze_temporal(self, segments: list[str]) -> dict:
        if not self.session or not segments:
            return {'freeze_count': 0, 'freeze_duration': 0, 'avg_frame_delta': 4.0}
        
        durations = []
        
        for seg_url in segments:
            try:
                timeout = aiohttp.ClientTimeout(total=5)
                start = time.time()
                async with self.session.head(seg_url, headers=HEADERS, timeout=timeout) as resp:
                    if resp.status == 200:
                        durations.append(time.time() - start)
            except:
                pass
        
        if not durations:
            return {'freeze_count': 0, 'freeze_duration': 0, 'avg_frame_delta': 4.0}
        
        avg = sum(durations) / len(durations)
        freeze_count = sum(1 for d in durations if d < 0.5)
        freeze_duration = sum(d for d in durations if d < 0.5)
        
        return {
            'freeze_count': freeze_count,
            'freeze_duration': freeze_duration,
            'avg_frame_delta': avg
        }
    
    async def analyze_cluster(self, cluster_id: str) -> int:
        streams = self.db.get_cluster_streams(cluster_id)
        
        if not streams:
            return 0
        
        urls = [s.stream_url for s in streams[:MAX_STREAMS_PER_CLUSTER]]
        
        tasks = [self.analyze_stream(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        analyzed = sum(1 for r in results if isinstance(r, StreamMetrics))
        
        print(f"[PrioritizedAnalyzer] Cluster {cluster_id}: {analyzed}/{len(urls)} analyzed")
        
        return analyzed
    
    async def analyze_by_priority(self, max_clusters: int = 20) -> dict:
        level_manager = LevelManager(self.db)
        
        priority_clusters = level_manager.get_analysis_priority()
        
        print(f"[PrioritizedAnalyzer] Analyzing top {max_clusters} clusters...")
        
        total = 0
        analyzed = 0
        
        for cluster_id, level in priority_clusters[:max_clusters]:
            count = await self.analyze_cluster(cluster_id)
            analyzed += count
            total += 1
            
            if total % 5 == 0:
                print(f"[PrioritizedAnalyzer] Progress: {total}/{max_clusters} clusters")
        
        return {
            'clusters': total,
            'streams': analyzed,
            'errors': self.stats['errors']
        }


async def main():
    import sys
    
    analyzer = PrioritizedAnalyzer()
    await analyzer.start()
    
    if len(sys.argv) > 1:
        cluster_id = sys.argv[1]
        await analyzer.analyze_cluster(cluster_id)
    else:
        result = await analyzer.analyze_by_priority(max_clusters=20)
        print(f"\n[Result]: {result}")
    
    await analyzer.stop()


if __name__ == '__main__':
    asyncio.run(main())