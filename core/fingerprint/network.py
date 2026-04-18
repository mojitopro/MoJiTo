import hashlib
import urllib.parse
from dataclasses import dataclass
from typing import Optional


@dataclass
class NetworkFingerprint:
    domain: str
    base_path: str
    full_hash: str
    scheme: str = 'https'


class NetworkFingerprinter:
    def __init__(self):
        self.cache = {}

    def fingerprint(self, url: str) -> Optional[NetworkFingerprint]:
        if not url:
            return None

        if url in self.cache:
            return self.cache[url]

        try:
            parsed = urllib.parse.urlparse(url)
        except Exception:
            return None

        domain = parsed.netloc or ''
        scheme = parsed.scheme or 'https'

        path = parsed.path or '/'
        if ';' in path:
            path = path.split(';')[0]

        base_path = self._extract_base_path(path)

        hash_input = f"{domain}:{base_path}"
        full_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]

        fp = NetworkFingerprint(
            domain=domain,
            base_path=base_path,
            full_hash=full_hash,
            scheme=scheme
        )

        self.cache[url] = fp
        return fp

    def _extract_base_path(self, path: str) -> str:
        segments = path.strip('/').split('/')

        if len(segments) <= 2:
            return path

        base_segments = segments[:2]
        return '/'.join(base_segments)

    def are_same_network(self, url1: str, url2: str) -> bool:
        fp1 = self.fingerprint(url1)
        fp2 = self.fingerprint(url2)

        if not fp1 or not fp2:
            return False

        return fp1.full_hash == fp2.full_hash

    def get_provider_hint(self, url: str) -> str:
        fp = self.fingerprint(url)
        if not fp:
            return 'unknown'

        domain = fp.domain.lower()

        providers = {
            'streama': 'streama',
            'xtream': 'xtream',
            'xtv': 'xtv',
            'm3u8': 'm3u8',
            'cdn': 'cdn',
            'cloudfront': 'cloudfront',
            'fastly': 'fastly',
            'akamai': 'akamai',
        }

        for key, provider in providers.items():
            if key in domain:
                return provider

        return 'custom'