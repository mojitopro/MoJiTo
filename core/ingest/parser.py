import re
import urllib.parse
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ParsedStream:
    url: str
    tvg_id: Optional[str] = None
    tvg_name: Optional[str] = None
    tvg_logo: Optional[str] = None
    group_title: Optional[str] = None
    quality: Optional[str] = None
    raw_attributes: dict = field(default_factory=dict)


@dataclass
class ParsedChannel:
    name: str
    streams: list = field(default_factory=list)
    aliases: list = field(default_factory=list)


class M3UParser:
    EXTINF_PATTERN = re.compile(
        r'#EXTINF:[^,]*,(?P<name>[^\n]*)'
        r'|tvg-id="(?P<tvg_id>[^"]*)"'
        r'|tvg-name="(?P<tvg_name>[^"]*)"'
        r'|tvg-logo="(?P<tvg_logo>[^"]*)"'
        r'|group-title="(?P<group_title>[^"]*)"'
        r'|\s+(?P<attr>[a-z_-]+)="[^"]*"'
    )

    QUALITY_PATTERN = re.compile(
        r'\b(4k|1080p|720p|576p|576i|480p|hd|sd)\b',
        re.IGNORECASE
    )

    def __init__(self):
        self.channels: dict[str, ParsedChannel] = {}

    def parse(self, m3u_content: str) -> dict[str, ParsedChannel]:
        self.channels = {}
        lines = m3u_content.splitlines()
        current_channel: Optional[ParsedChannel] = None
        current_attrs: dict = {}

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith('#EXTINF:'):
                current_attrs = self._parse_extinf(line)
                quality = self._extract_quality(current_attrs.get('name', ''))
                current_attrs['quality'] = quality

                stream = ParsedStream(
                    url='',
                    tvg_id=current_attrs.get('tvg_id'),
                    tvg_name=current_attrs.get('tvg_name'),
                    tvg_logo=current_attrs.get('tvg_logo'),
                    group_title=current_attrs.get('group_title'),
                    quality=quality,
                    raw_attributes=current_attrs
                )

                name = current_attrs.get('tvg_name') or current_attrs.get('name', 'Unknown')
                if name not in self.channels:
                    self.channels[name] = ParsedChannel(name=name)
                self.channels[name].streams.append(stream)

            elif line.startswith('http'):
                if self.channels and current_attrs:
                    last_ch = list(self.channels.values())[-1]
                    if last_ch.streams:
                        last_ch.streams[-1].url = line

        self._post_process()
        return self.channels

    def _parse_extinf(self, line: str) -> dict:
        attrs = {'name': ''}

        name_match = re.search(r'#EXTINF:[^,]*,(.+)', line)
        if name_match:
            attrs['name'] = name_match.group(1).strip()

        tvg_id_match = re.search(r'tvg-id="([^"]*)"', line)
        if tvg_id_match:
            attrs['tvg_id'] = tvg_id_match.group(1)

        tvg_name_match = re.search(r'tvg-name="([^"]*)"', line)
        if tvg_name_match:
            attrs['tvg_name'] = tvg_name_match.group(1)

        tvg_logo_match = re.search(r'tvg-logo="([^"]*)"', line)
        if tvg_logo_match:
            attrs['tvg_logo'] = tvg_logo_match.group(1)

        group_match = re.search(r'group-title="([^"]*)"', line)
        if group_match:
            attrs['group_title'] = group_match.group(1)

        return attrs

    def _extract_quality(self, name: str) -> Optional[str]:
        match = self.QUALITY_PATTERN.search(name)
        return match.group(1).lower() if match else None

    def _post_process(self):
        for channel in self.channels.values():
            alias = channel.name.lower().strip()
            channel.aliases.append(alias)

            if 'hd' in alias:
                channel.aliases.append(alias.replace('hd', '').strip())
            if 'hd' in alias:
                channel.aliases.append(alias.replace('hd', '').strip())

    def parse_file(self, filepath: str) -> dict[str, ParsedChannel]:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return self.parse(content)

    def to_normalized_dict(self) -> dict:
        result = {}
        for name, channel in self.channels.items():
            result[name] = {
                'aliases': list(set(channel.aliases)),
                'streams': [
                    {
                        'url': s.url,
                        'type': self._detect_stream_type(s.url),
                        'tvg_id': s.tvg_id,
                        'quality': s.quality,
                        'group': s.group_title,
                    }
                    for s in channel.streams if s.url
                ]
            }
        return result

    def _detect_stream_type(self, url: str) -> str:
        if not url:
            return 'unknown'
        lower = url.lower()
        if '.m3u8' in lower or 'manifest' in lower:
            return 'm3u8'
        elif '.ts' in lower:
            return 'ts'
        elif '.mp4' in lower:
            return 'mp4'
        return 'unknown'