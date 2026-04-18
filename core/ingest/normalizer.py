import re
import hashlib
import uuid
from typing import Optional


QUALITY_PATTERN = re.compile(
    r'\b(4k|1080p|720p|576p|576i|480p|hd|sd)\b',
    re.IGNORECASE
)

COUNTRY_SUFFIXES = re.compile(
    r'\s*-\s*[a-z]{2}(?:\s+\([^)]+\))?$'
)

PREFIX_NUMBERS = re.compile(
    r'^\d+[\.\)]?\s*|^\d+\s+'
)


class ChannelNormalizer:
    def __init__(self):
        self.cache = {}

    def normalize(self, name: str) -> str:
        if not name:
            return ''

        text = str(name).lower().strip()
        text = text.replace('&t.', 'nt.')

        text = COUNTRY_SUFFIXES.sub('', text)
        text = PREFIX_NUMBERS.sub('', text)
        text = re.sub(r'\s+\([^)]+\)$', '', text)
        text = re.sub(r'\s+[0-9a-f]{6,}(?:.*)?$', '', text)
        text = re.sub(r'\b(1080p|720p|576p|576i|480p|4k|hd|sd)\b', '', text)
        text = re.sub(r'\b(clone|enviado|sps|sj|cp|ip)\b', '', text)
        text = re.sub(r'[^a-z0-9+ ]+', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def extract_quality(self, name: str) -> Optional[str]:
        match = QUALITY_PATTERN.search(name)
        return match.group(1).lower() if match else None

    def generate_channel_id(self, name: str) -> str:
        normalized = self.normalize(name)
        hash_input = normalized.encode('utf-8')
        return hashlib.sha256(hash_input).hexdigest()[:12]

    def get_aliases(self, name: str) -> list[str]:
        normalized = self.normalize(name)
        aliases = [normalized]

        if 'hd' in normalized:
            aliases.append(normalized.replace('hd', '').strip())

        if 'hd' not in normalized and 'hd' in name.lower():
            aliases.append(normalized + ' hd')

        return list(set(aliases))

    def are_similar(self, name1: str, name2: str, threshold: float = 0.8) -> bool:
        norm1 = self.normalize(name1)
        norm2 = self.normalize(name2)

        if norm1 == norm2:
            return True

        distance = self._levenshtein_distance(norm1, norm2)
        max_len = max(len(norm1), len(norm2))
        similarity = 1 - (distance / max_len) if max_len > 0 else 0

        return similarity >= threshold

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]