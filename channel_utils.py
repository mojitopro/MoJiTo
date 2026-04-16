import math
import re
from functools import lru_cache

STATUS_ORDER = {
    'online': 0,
    'unknown': 1,
    'offline': 2,
    'error': 3,
    'timeout': 4,
    'not_found': 5,
}

PREMIUM_HINTS = (
    r'\bhbo\b',
    r'\bcinemax\b',
    r'\bshowtime\b',
    r'\bstar channel\b',
    r'\bamedia premium\b',
    r'\bnhk world premium\b',
)


def normalize_channel_name(name):
    if not name:
        return ''

    text = str(name).lower().strip()
    text = text.replace('&t.', 'nt.')

    # Strip country suffixes like "-CO", "-MX", "-US" and quality tags.
    text = re.sub(r'\s*-\s*[a-z]{2}(?:\s+\([^)]+\))?$', '', text)
    text = re.sub(r'^\d+[\.\)]?\s*', '', text)
    text = re.sub(r'^\d+\s+', '', text)
    text = re.sub(r'\s+\([^)]+\)$', '', text)
    text = re.sub(r'\s+[0-9a-f]{6,}(?:.*)?$', '', text)
    text = re.sub(r'\b(1080p|720p|576p|576i|480p|4k|hd|sd)\b', '', text)
    text = re.sub(r'\b(clone|enviado|sps|sj|cp|ip)\b', '', text)
    text = re.sub(r'[^a-z0-9+ ]+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


@lru_cache(maxsize=1)
def _premium_catalog_names():
    try:
        from catalog import get_all_channel_names
    except Exception:
        return frozenset()

    names = set()
    for item in get_all_channel_names():
        if item.get('category') == 'premium':
            names.add(normalize_channel_name(item.get('name', '')))
    return frozenset(names)


def is_premium_channel(name, category=None):
    normalized = normalize_channel_name(name)
    if not normalized:
        return False

    if category and str(category).lower() == 'premium':
        return True

    if normalized in _premium_catalog_names():
        return True

    for hint in PREMIUM_HINTS:
        if re.search(hint, normalized):
            return True

    return False


def normalize_latency_ms(latency):
    if latency is None:
        return None

    try:
        value = float(latency)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(value) or value <= 0:
        return None

    # Values below 10 are usually measured in seconds; normalize them to ms.
    if value < 10:
        value *= 1000.0

    # 999 is used as an "unknown" sentinel in several ingest paths.
    if value >= 900:
        return None

    return value


def stream_sort_key(stream):
    status = str(stream.get('status') or 'unknown').lower()
    score = float(stream.get('score') or 0)
    latency = normalize_latency_ms(stream.get('latency'))
    url = stream.get('url') or ''
    return (
        STATUS_ORDER.get(status, 1),
        -score,
        latency if latency is not None else 999999,
        url,
    )
