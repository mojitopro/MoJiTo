import json, time
from pathlib import Path

CACHE_FILE = 'cache.json'
CACHE_TTL = 900

cache = None

def load():
    global cache
    if cache is None:
        p = Path(CACHE_FILE)
        cache = json.loads(p.read_text()) if p.exists() else {}
    return cache

def get_cached(key):
    c = load()
    if key in c:
        entry = c[key]
        if time.time() - entry.get('ts', 0) < CACHE_TTL:
            return entry.get('data')
    return None

def set_cached(key, data):
    c = load()
    c[key] = {'data': data, 'ts': time.time(), 'expires': CACHE_TTL}
    Path(CACHE_FILE).write_text(json.dumps(c))

def get_fallback(key):
    c = load()
    return c[key].get('data') if key in c else None