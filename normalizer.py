import sqlite3
import re
import os
from collections import defaultdict

DB_PATH = os.environ.get('DB_PATH', 'streams.db')

def normalize_channel_name(name):
    name = name.lower().strip()
    
    # Remove country codes like -CO, -MX, -US, etc.
    name = re.sub(r'\s*-\s*[A-Z]{2}(\s+\([^)]+\))?$', '', name)
    
    # Remove numbers at the start like "010 ", "2.28 ", "117)"
    name = re.sub(r'^\d+\.?\s*', '', name)
    name = re.sub(r'^\d+\)\s+', '', name)
    
    # Remove hashed/encrypted names like "47dllnef", "945a2db..."
    name = re.sub(r'\s+[0-9a-f]{6,}.*$', '', name)
    
    # Remove quality indicators
    name = re.sub(r'\s*(hd|sd|4k|1080p|720p)$', '', name, flags=re.IGNORECASE)
    
    # Remove common suffixes
    name = re.sub(r'\s+(clone|enviado|sps|sj|cp|ip|sd|hd)$', '', name, flags=re.IGNORECASE)
    
    # Clean up &T -> NT
    name = name.replace('&t.', 'nt.')
    
    # Normalize similar names
    name = name.replace('cartoon network', 'cartoon network')
    name = name.replace('cartoonito', 'cartoonito')
    name = name.replace('adult swim', 'adult swim')
    name = name.replace('nt.', 'nt ')
    
    # Remove extra spaces
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name

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
        items.sort(key=lambda x: x['latency'])
        unified[norm_ch] = items
    
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