import asyncio
import aiohttp
from dataclasses import dataclass, field
from typing import Optional
from collections import deque


@dataclass
class FusedStream:
    active_url: str
    backup_urls: list[str]
    buffer: deque
    switch_count: int = 0


class StreamFuser:
    def __init__(
        self,
        buffer_size: int = 30,
        switch_threshold: float = 0.3,
        check_interval: float = 5.0
    ):
        self.buffer_size = buffer_size
        self.switch_threshold = switch_threshold
        self.check_interval = check_interval
        self.active_streams: dict[str, FusedStream] = {}

    def add_stream_option(self, channel_id: str, url: str) -> None:
        if channel_id not in self.active_streams:
            self.active_streams[channel_id] = FusedStream(
                active_url=url,
                backup_urls=[],
                buffer=deque(maxlen=self.buffer_size)
            )
        else:
            fused = self.active_streams[channel_id]
            if url != fused.active_url and url not in fused.backup_urls:
                fused.backup_urls.append(url)

    def select_best_stream(
        self,
        channel_id: str,
        metrics: dict
    ) -> Optional[str]:
        if channel_id not in self.active_streams:
            return None

        fused = self.active_streams[channel_id]
        candidates = [fused.active_url] + fused.backup_urls

        best_url = None
        best_score = -1

        for url in candidates:
            m = metrics.get(url)
            if not m:
                continue

            score = self._calculate_score(m)
            if score > best_score:
                best_score = score
                best_url = url

        if best_url and best_url != fused.active_url:
            fused.switch_count += 1

        return best_url or fused.active_url

    def _calculate_score(self, metrics: dict) -> float:
        score = 0.0

        if metrics.get('valid_stream'):
            score += 0.4

        stability = metrics.get('stability', 0)
        score += stability * 0.3

        motion = metrics.get('motion_score', 0)
        score += motion * 0.2

        startup = metrics.get('startup_time', 999)
        if startup < 5:
            score += 0.1

        freeze = metrics.get('freeze_events', 999)
        if freeze < 3:
            score += 0.1

        return score

    async def check_streams(
        self,
        channel_id: str,
        evaluator
    ) -> Optional[str]:
        if channel_id not in self.active_streams:
            return None

        fused = self.active_streams[channel_id]
        all_urls = [fused.active_url] + fused.backup_urls

        timeout = aiohttp.ClientTimeout(total=5)

        for url in all_urls:
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.head(url) as resp:
                        if resp.status in [200, 206]:
                            return url
            except Exception:
                pass

        return None

    def failover(self, channel_id: str, failed_url: str) -> Optional[str]:
        if channel_id not in self.active_streams:
            return None

        fused = self.active_streams[channel_id]

        if failed_url == fused.active_url and fused.backup_urls:
            fused.active_url = fused.backup_urls.pop(0)
            fused.switch_count += 1
            return fused.active_url

        if failed_url in fused.backup_urls:
            fused.backup_urls.remove(failed_url)

        return fused.active_url

    def get_stats(self, channel_id: str) -> dict:
        if channel_id not in self.active_streams:
            return {}

        fused = self.active_streams[channel_id]
        return {
            'active_url': fused.active_url,
            'backup_count': len(fused.backup_urls),
            'switch_count': fused.switch_count,
            'buffer_usage': len(fused.buffer) / self.buffer_size
        }