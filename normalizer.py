import sqlite3
import os
from collections import defaultdict

from channel_utils import is_premium_channel, normalize_channel_name as _normalize_channel_name, stream_sort_key

DB_PATH = os.environ.get('DB_PATH', 'streams.db')

def normalize_channel_name(name):
    return _normalize_channel_name(name)

def build_unified_index():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM channels")
    
    cursor.execute("SELECT channel, url, status, latency FROM streams WHERE status='online'")
    streams = cursor.fetchall()
    
    grouped = defaultdict(list)
    for ch, url, status, lat in streams:
        normalized = normalize_channel_name(ch)
        if normalized:
            grouped[normalized].append({
                'url': url,
                'latency': lat if lat else 999
            })
    
    unified = {}
    for norm_ch, items in grouped.items():
        items.sort(key=stream_sort_key)
        unified[norm_ch] = items
    
    for ch, items in unified.items():
        cursor.execute("""
            INSERT INTO channels (name, stream_count, best_url, category)
            VALUES (?, ?, ?, ?)
        """, (
            ch,
            len(items),
            items[0]['url'] if items else None,
            'premium' if is_premium_channel(ch) else 'general',
        ))
    
    conn.commit()
    print(f"Unificados a {len(unified)} canales")
    return len(unified)

def get_unified_channels():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM channels ORDER BY name")
    return [r[0] for r in cursor.fetchall()]

def get_best_stream_for_channel(channel_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    normalized = normalize_channel_name(channel_name)
    
    cursor.execute("SELECT best_url FROM channels WHERE name=?", (normalized,))
    result = cursor.fetchone()
    
    if result and result[0]:
        return result[0]
    
    cursor.execute("""
        SELECT url, latency FROM streams 
        WHERE LOWER(channel) LIKE ?
        AND status='online'
        ORDER BY latency
        LIMIT 1
    """, (f'%{normalized}%',))
    result = cursor.fetchone()
    
    if result:
        return result[0]
    return None

if __name__ == '__main__':
    build_unified_index()
