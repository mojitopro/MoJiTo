import os
import json
import time
from pathlib import Path

CACHE_FILE = 'cache.json'
CACHE_TTL = 900  # 15 minutes

cache = {}

def load_cache():
    global cache
    p = Path(CACHE_FILE)
    if p.exists():
        try:
            cache = json.loads(p.read_text())
        except:
            cache = {}
    return cache

def save_cache(data):
    try:
        Path(CACHE_FILE).write_text(json.dumps(data, indent=2))
    except:
        pass

def get_cached(key):
    load_cache()
    if key in cache:
        entry = cache[key]
        if time.time() - entry.get('ts', 0) < CACHE_TTL:
            return entry.get('data')
    return None

def set_cached(key, data):
    load_cache()
    cache[key] = {'data': data, 'ts': time.time(), 'expires': CACHE_TTL}
    save_cache(cache)

def get_fallback(key):
    load_cache()
    if key in cache:
        return cache[key].get('data')
    return None