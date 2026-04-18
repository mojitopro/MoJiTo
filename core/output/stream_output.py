import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from urllib.parse import urlparse


class OutputFormat(Enum):
    M3U = 'm3u'
    JSON = 'json'
    HLS = 'hls'
    DASH = 'dash'


@dataclass
class StreamOutput:
    channel_id: str
    name: str
    primary_url: str
    backup_urls: list[str] = field(default_factory=list)
    logo: Optional[str] = None
    group: Optional[str] = None
    quality: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            'channel_id': self.channel_id,
            'name': self.name,
            'url': self.primary_url,
            'fallbacks': self.backup_urls,
            'logo': self.logo,
            'group': self.group,
            'quality': self.quality
        }

    def to_m3u_entry(self) -> str:
        extinf = f'#EXTINF:-1 tvg-name="{self.name}"'
        
        if self.logo:
            extinf += f' tvg-logo="{self.logo}"'
        if self.group:
            extinf += f' group-title="{self.group}"'
        
        extinf += f',{self.name}'
        
        lines = [extinf, self.primary_url]
        
        for backup in self.backup_urls:
            lines.append(backup)
        
        return '\n'.join(lines)

    def to_m3u(self, streams: list['StreamOutput']) -> str:
        lines = ['#EXTM3U']
        
        for stream in streams:
            lines.append(stream.to_m3u_entry())
        
        return '\n'.join(lines)


class OutputManager:
    def __init__(self):
        self.streams: dict[str, StreamOutput] = {}

    def add_stream(self, stream: StreamOutput) -> None:
        self.streams[stream.channel_id] = stream

    def add_channel(
        self,
        channel_id: str,
        name: str,
        url: str,
        fallback: Optional[list[str]] = None,
        logo: Optional[str] = None,
        group: Optional[str] = None,
        quality: Optional[str] = None
    ) -> None:
        stream = StreamOutput(
            channel_id=channel_id,
            name=name,
            primary_url=url,
            backup_urls=fallback or [],
            logo=logo,
            group=group,
            quality=quality
        )
        self.streams[channel_id] = stream

    def get_by_channel_id(self, channel_id: str) -> Optional[StreamOutput]:
        return self.streams.get(channel_id)

    def to_json(self, pretty: bool = True) -> str:
        data = {
            'channels': [s.to_dict() for s in self.streams.values()]
        }
        indent = 2 if pretty else None
        return json.dumps(data, indent=indent, ensure_ascii=False)

    def to_m3u(self) -> str:
        lines = ['#EXTM3U']
        
        for stream in self.streams.values():
            lines.append(stream.to_m3u_entry())
        
        return '\n'.join(lines)

    def export_json(self, filepath: str) -> None:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.to_json())

    def export_m3u(self, filepath: str) -> None:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.to_m3u())

    def filter_by_group(self, group: str) -> list[StreamOutput]:
        return [s for s in self.streams.values() if s.group == group]

    def filter_by_quality(self, quality: str) -> list[StreamOutput]:
        return [s for s in self.streams.values() if s.quality == quality]

    def get_groups(self) -> list[str]:
        groups = set()
        for stream in self.streams.values():
            if stream.group:
                groups.add(stream.group)
        return sorted(groups)