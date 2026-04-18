import hashlib
import re
from urllib.parse import urlparse


def hash_url(url: str) -> str:
    if not url:
        return ''
    return hashlib.sha256(url.encode()).hexdigest()[:12]


def extract_domain(url: str) -> str:
    try:
        return urlparse(url).netloc
    except:
        return ''


def extract_base_path(url: str) -> str:
    try:
        parsed = urlparse(url)
        path = parsed.path or '/'
        if ';' in path:
            path = path.split(';')[0]
        segments = path.strip('/').split('/')
        if len(segments) <= 2:
            return path
        return '/'.join(segments[:2])
    except:
        return '/'


def detect_stream_type(url: str) -> str:
    if not url:
        return 'unknown'
    lower = url.lower()
    if '.m3u8' in lower or 'manifest' in lower:
        return 'm3u8'
    elif '.ts' in lower:
        return 'ts'
    elif '.mp4' in lower:
        return 'mp4'
    return 'ts'


def is_valid_url(url: str) -> bool:
    if not url:
        return False
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme in ['http', 'https'] and parsed.netloc)
    except:
        return False


def normalize_channel_name(name: str) -> str:
    if not name:
        return ''
    text = str(name).lower().strip()
    text = re.sub(r'\s*-\s*[a-z]{2}(?:\s+\([^)]+\))?$', '', text)
    text = re.sub(r'^\d+[\.\)]?\s*', '', text)
    text = re.sub(r'\s+\([^)]+\)$', '', text)
    text = re.sub(r'\b(1080p|720p|576p|576i|480p|4k|hd|sd)\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'[^a-z0-9+ ]+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def levenshtein_distance(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
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


def string_similarity(s1: str, s2: str) -> float:
    if not s1 or not s2:
        return 0.0
    distance = levenshtein_distance(s1, s2)
    max_len = max(len(s1), len(s2))
    return 1 - (distance / max_len) if max_len > 0 else 0.0


def calculate_stream_score(
    latency_ms: float,
    avg_frame_delta: float,
    freeze_duration: float,
    black_ratio: float,
    motion_score: float = 0.5,
    stability: float = 0.5
) -> float:
    score = (
        - latency_ms * 0.01
        + avg_frame_delta * 70
        - freeze_duration * 10
        - black_ratio * 150
        + motion_score * 20
        + stability * 15
    )
    return max(0.0, min(100.0, score))