#!/usr/bin/env python3
"""
Analyzer Service
Visual analysis - captures frames and computes metrics
"""
import asyncio
import aiohttp
import time
import hashlib
import subprocess
import tempfile
import os
from typing import Optional
from pathlib import Path

from runtime.db import Database, StreamMetrics
from runtime.utils import calculate_stream_score


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (SMART-TV) AppleWebKit/537.36',
    'Accept': '*/*',
    'Connection': 'keep-alive',
}


class AnalyzerService:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
        self.session: Optional[aiohttp.ClientSession] = None
        self.temp_dir = tempfile.mkdtemp(prefix='mojito_')
        self.running = False
    
    async def start(self):
        self.session = aiohttp.ClientSession()
        self.running = True
        print("[Analyzer] Started")
    
    async def stop(self):
        self.running = False
        if self.session:
            await self.session.close()
        
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        
        print("[Analyzer] Stopped")
    
    async def analyze_stream(self, url: str, duration: int = 15) -> StreamMetrics:
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
                    temporal = await self._analyze_temporal(segments[:5])
                    metrics.freeze_count = temporal.get('freeze_count', 0)
                    metrics.freeze_duration = temporal.get('freeze_duration', 0)
                    metrics.avg_frame_delta = temporal.get('avg_frame_delta', 0)
                
                frames = await self._capture_frames(url, duration)
                if frames:
                    visual = self._analyze_frames(frames)
                    metrics.black_ratio = visual.get('black_ratio', 0)
                    metrics.motion_score = visual.get('motion_score', 0)
                    metrics.stability = visual.get('stability', 0)
            
            self.db.insert_stream_metrics(metrics)
        
        except Exception as e:
            print(f"[Analyzer] Error analyzing {url}: {e}")
        
        return metrics
    
    async def _measure_startup(self, url: str) -> Optional[float]:
        if not self.session:
            return None
        
        try:
            start = time.time()
            timeout = aiohttp.ClientTimeout(total=10)
            
            async with self.session.get(url, headers=HEADERS, timeout=timeout) as resp:
                if resp.status in [200, 206]:
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
        
        return segments
    
    async def _analyze_temporal(self, segments: list[str]) -> dict:
        if not self.session or not segments:
            return {}
        
        durations = []
        prev_time = time.time()
        
        timeout = aiohttp.ClientTimeout(total=5)
        async with self.session.head(segments[0], headers=HEADERS, timeout=timeout) as resp:
            if resp.status != 200:
                return {'freeze_count': 0, 'freeze_duration': 0, 'avg_frame_delta': 4.0}
        
        for seg_url in segments[1:]:
            try:
                curr_time = time.time()
                durations.append(curr_time - prev_time)
                prev_time = curr_time
                
                timeout = aiohttp.ClientTimeout(total=5)
                async with self.session.head(seg_url, headers=HEADERS, timeout=timeout):
                    pass
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
    
    async def _capture_frames(self, url: str, duration: int = 15) -> list[str]:
        frames = []
        
        output_pattern = os.path.join(self.temp_dir, 'frame_%04d.jpg')
        
        try:
            cmd = [
                'ffmpeg', '-y',
                '-i', url,
                '-t', str(duration),
                '-vf', 'fps=1',
                output_pattern
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=duration + 10
            )
            
            if result.returncode == 0:
                for f in sorted(Path(self.temp_dir).glob('frame_*.jpg')):
                    frames.append(str(f))
        
        except Exception as e:
            print(f"[Analyzer] ffmpeg error: {e}")
        
        return frames
    
    def _analyze_frames(self, frames: list[str]) -> dict:
        if not frames:
            return {'black_ratio': 0, 'motion_score': 0.5, 'stability': 0.5}
        
        black_count = 0
        prev_hist = None
        motion_diffs = []
        
        for frame in frames:
            try:
                cmd = ['ffprobe', '-frames:v', '1', '-show_entries', 'frame=pict_type,histogram', '-of', 'json', frame]
                result = subprocess.run(cmd, capture_output=True, timeout=5)
                
                if result.returncode != 0:
                    continue
                
                output = result.stdout.decode()
                
                if 'I' not in output and 'P' not in output and 'B' not in output:
                    black_count += 1
                
                if prev_hist:
                    diff = abs(len(output) - len(prev_hist)) / max(len(prev_hist), 1)
                    motion_diffs.append(diff)
                
                prev_hist = output
            
            except:
                pass
        
        black_ratio = black_count / len(frames) if frames else 0
        motion_score = sum(motion_diffs) / len(motion_diffs) if motion_diffs else 0.5
        stability = 1.0 - (black_ratio * 0.5)
        
        return {
            'black_ratio': black_ratio,
            'motion_score': min(1.0, motion_score * 10),
            'stability': stability
        }
    
    async def analyze_all(self, batch_size: int = 10) -> dict:
        streams = self.db.get_all_streams(status='online')
        results = {'analyzed': 0, 'errors': 0}
        
        for i, stream in enumerate(streams[:batch_size]):
            try:
                await self.analyze_stream(stream.url)
                results['analyzed'] += 1
            except Exception as e:
                results['errors'] += 1
            
            if (i + 1) % 5 == 0:
                print(f"[Analyzer] Analyzed {i+1}/{min(batch_size, len(streams))}...")
        
        return results
    
    def get_metrics(self, url: str) -> Optional[StreamMetrics]:
        return self.db.get_stream_metrics(url)


async def main():
    import sys
    
    db = Database()
    analyzer = AnalyzerService(db)
    await analyzer.start()
    
    if len(sys.argv) > 1:
        url = sys.argv[1]
        metrics = await analyzer.analyze_stream(url)
        print(f"[Analyzer] Metrics: startup={metrics.startup_time:.2f}s, freeze={metrics.freeze_count}, "
              f"black={metrics.black_ratio:.2f}, motion={metrics.motion_score:.2f}")
    else:
        results = await analyzer.analyze_all(batch_size=20)
        print(f"[Analyzer] Results: {results}")
    
    await analyzer.stop()


if __name__ == '__main__':
    asyncio.run(main())