import hashlib
import asyncio
import aiohttp
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TemporalFingerprint:
    durations: list[float] = field(default_factory=list)
    sizes: list[int] = field(default_factory=list)
    avg_duration: float = 0.0
    avg_size: int = 0
    variance: float = 0.0
    full_hash: str = ''


class TemporalFingerprinter:
    def __init__(self, segment_count: int = 5, timeout: float = 5.0):
        self.segment_count = segment_count
        self.timeout = timeout
        self.cache = {}

    async def fingerprint_async(self, url: str) -> Optional[TemporalFingerprint]:
        if not url:
            return None

        if url in self.cache:
            return self.cache[url]

        segments_urls = await self._get_segment_urls(url)
        if not segments_urls:
            return None

        durations = []
        sizes = []

        timeout = aiohttp.ClientTimeout(total=self.timeout)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            for seg_url in segments_urls[:self.segment_count]:
                duration, size = await self._fetch_segment_info(session, seg_url)
                if duration is not None:
                    durations.append(duration)
                    sizes.append(size)

        if not durations:
            return None

        avg_duration = sum(durations) / len(durations)
        avg_size = sum(sizes) / len(sizes)

        variance = sum((d - avg_duration) ** 2 for d in durations) / len(durations)

        hash_input = f"{avg_duration:.2f}:{avg_size}:{variance:.2f}"
        full_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]

        fp = TemporalFingerprint(
            durations=durations,
            sizes=sizes,
            avg_duration=avg_duration,
            avg_size=int(avg_size),
            variance=variance,
            full_hash=full_hash
        )

        self.cache[url] = fp
        return fp

    def fingerprint(self, url: str) -> Optional[TemporalFingerprint]:
        try:
            return asyncio.get_event_loop().run_until_complete(
                self.fingerprint_async(url)
            )
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.fingerprint_async(url))
            finally:
                loop.close()

    async def _get_segment_urls(self, m3u8_url: str) -> list[str]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(m3u8_url) as resp:
                    if resp.status != 200:
                        return []
                    content = await resp.text()
        except Exception:
            return []

        base_url = m3u8_url.rsplit('/', 1)[0] + '/' if '/' in m3u8_url else ''

        segments = []
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith('#'):
                if line.startswith('http'):
                    segments.append(line)
                else:
                    segments.append(base_url + line)

        return segments

    async def _fetch_segment_info(
        self, session: aiohttp.ClientSession, url: str
    ) -> tuple[Optional[float], Optional[int]]:
        try:
            import time
            start = time.time()
            async with session.head(url) as resp:
                size = int(resp.headers.get('Content-Length', 0))
            duration = time.time() - start
            return duration, size
        except Exception:
            return None, None

    def are_similar(self, fp1: TemporalFingerprint, fp2: TemporalFingerprint) -> bool:
        if not fp1 or not fp2:
            return False

        if fp1.full_hash == fp2.full_hash:
            return True

        duration_diff = abs(fp1.avg_duration - fp2.avg_duration)
        if duration_diff > 1.0:
            return False

        return True