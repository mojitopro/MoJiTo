import sqlite3
import re
import os
from collections import defaultdict

DB_PATH = os.environ.get('DB_PATH', 'streams.db')

def normalize_channel_name(name):
    name = name.lower().strip()
    
    name = re.sub(r'\s*-\s*[A-Z]{2}$', '', name)
    name = re.sub(r'\s*\([A-Z]{2}\)\s*$', '', name)
    
    name = re.sub(r'^\d+\.?\s*', '', name)
    name = re.sub(r'\s*\d+$', '', name)
    name = re.sub(r'\s+[\da-f]{6,}$', '', name)
    name = re.sub(r'\s+\d+[a-f]{6,}$', '', name)
    
    name = re.sub(r'\s+(hd|sd|hd\s*-\s*\w+)$', '', name)
    name = re.sub(r'(hd|sd|4k|1080p|720p)\s*$', '', name)
    
    name = re.sub(r'\s+clone\s*$', '', name)
    name = re.sub(r'\s+enviado\s*$', '', name)
    name = re.sub(r'\s+sps\s*$', '', name)
    name = re.sub(r'\s+sj\s*$', '', name)
    name = re.sub(r'\s+cp\s*$', '', name)
    name = re.sub(r'\s+\d+db\w+$', '', name)
    
    name = name.replace('&t.', 'nt.')
    name = re.sub(r'\s+', ' ', name)
    name = name.strip()
    
    return name

def build_unified_index():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT channel, url, status, latency FROM streams WHERE status='online'")
    streams = cursor.fetchall()
    
    grouped = defaultdict(list)
    for ch, url, status, lat in streams:
        normalized = normalize_channel_name(ch)
        grouped[normalized].append({
            'url': url,
            'latency': lat if lat else 999
        })
    
    unified = {}
    for norm_ch, items in grouped.items():
        items.sort(key=lambda x: x['latency'])
        unified[norm_ch] = items
    
    cursor.execute("DELETE FROM channels")
    for ch, items in unified.items():
        cursor.execute("""
            INSERT INTO channels (name, stream_count, best_url)
            VALUES (?, ?, ?)
        """, (ch, len(items), items[0]['url'] if items else None))
    
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