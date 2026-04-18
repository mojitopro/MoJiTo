import asyncio
import aiohttp
import time
import hashlib
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StreamMetrics:
    startup_time: float = 0.0
    freeze_events: int = 0
    motion_score: float = 0.0
    stability: float = 0.0
    valid_stream: bool = False
    url: str = ''
    error: Optional[str] = None


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (SMART-TV) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': '*/*',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
}


class StreamEvaluator:
    def __init__(
        self,
        timeout: float = 10.0,
        sample_duration: float = 10.0,
        freeze_threshold: float = 0.01
    ):
        self.timeout = timeout
        self.sample_duration = sample_duration
        self.freeze_threshold = freeze_threshold
        self.cache = {}

    async def evaluate_async(self, url: str) -> StreamMetrics:
        if not url:
            return StreamMetrics(url=url, error='empty_url')

        if url in self.cache:
            return self.cache[url]

        metrics = StreamMetrics(url=url)

        try:
            await self._measure_startup(metrics)
            if metrics.valid_stream:
                await self._analyze_content(metrics)
        except Exception as e:
            metrics.error = str(e)[:50]

        self.cache[url] = metrics
        return metrics

    def evaluate(self, url: str) -> StreamMetrics:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                raise RuntimeError("Cannot run in async context")
            return loop.run_until_complete(self.evaluate_async(url))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.evaluate_async(url))
            finally:
                loop.close()

    async def _measure_startup(self, metrics: StreamMetrics):
        start = time.time()

        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(metrics.url, headers=HEADERS) as resp:
                    if resp.status not in [200, 206]:
                        metrics.error = f'http_{resp.status}'
                        return

                    content_type = resp.headers.get('Content-Type', '')

                    if '.m3u8' in metrics.url or 'application/vnd' in content_type:
                        metrics.valid_stream = True
                        metrics.startup_time = time.time() - start
                        return

                    data_received = 0
                    async for chunk in resp.content.iter_chunked(65536):
                        data_received += len(chunk)
                        if data_received > 100000:
                            metrics.valid_stream = True
                            metrics.startup_time = time.time() - start
                            break

        except asyncio.TimeoutError:
            metrics.error = 'timeout'
        except Exception as e:
            metrics.error = str(e)[:30]

    async def _analyze_content(self, metrics: StreamMetrics):
        if not metrics.valid_stream:
            return

        if '.m3u8' not in metrics.url:
            metrics.stability = 0.9
            metrics.motion_score = 0.5
            return

        try:
            segments = await self._get_hls_segments(metrics.url)
            if not segments:
                return

            await self._measure_temporal(segments, metrics)
        except Exception:
            pass

    async def _get_hls_segments(self, manifest_url: str) -> list[str]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(manifest_url, headers=HEADERS) as resp:
                    if resp.status != 200:
                        return []
                    content = await resp.text()
        except Exception:
            return []

        base_url = manifest_url.rsplit('/', 1)[0] + '/'
        segments = []

        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith('#'):
                if line.startswith('http'):
                    segments.append(line)
                else:
                    segments.append(base_url + line)

        return segments[:10]

    async def _measure_temporal(self, segments: list, metrics: StreamMetrics):
        if not segments:
            return

        durations = []
        prev_time = time.time()

        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for seg_url in segments[:5]:
                try:
                    async with session.head(seg_url, headers=HEADERS) as resp:
                        if resp.status == 200:
                            curr_time = time.time()
                            durations.append(curr_time - prev_time)
                            prev_time = curr_time
                except Exception:
                    pass

        if not durations:
            metrics.stability = 0.0
            return

        if len(durations) > 1:
            avg = sum(durations) / len(durations)
            variance = sum((d - avg) ** 2 for d in durations) / len(durations)
            metrics.stability = 1.0 - min(variance, 1.0)
            metrics.freeze_events = sum(1 for d in durations if d > self.freeze_threshold)

        metrics.motion_score = 0.7 if metrics.stability > 0.5 else 0.3