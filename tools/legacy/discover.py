import requests
import sqlite3
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from db import get_connection

PATHS = [
    "play/a01", "play/a02", "play/a03", "play/a04", "play/a05",
    "play/a06", "play/a07", "play/a08", "play/a09", "play/a10",
    "play/a0a", "play/a0b", "play/a0c", "play/a0d", "play/a0e",
    "play/a0f", "play/a0g", "play/a0h", "play/a0i", "play/a0j",
    "play/a0k", "play/a0l", "play/a0m", "play/a0n", "play/a0o",
    "play/a0p", "play/a0q", "play/a0r", "play/a0s", "play/a0t",
    "play/index.m3u8", "live/playlist.m3u8", "live/index.m3u8",
    "live/test.m3u8", "playlist.m3u8", "index.m3u8",
    "stream/playlist.m3u8", "stream/chunk.m3u8"
]

def check_path(ip, port, path):
    url = f"http://{ip}:{port}/{path}"
    try:
        r = requests.head(url, timeout=1, allow_redirects=True)
        if r.status_code == 200:
            return url
    except:
        pass
    return None

def discover_node(node):
    ip, port = node['ip'], node['port']
    found = []
    for path in PATHS:
        result = check_path(ip, port, path)
        if result:
            found.append(result)
    return ip, found

def discover(limit=100, workers=20):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT ip, port FROM nodes LIMIT ?", (limit,))
    nodes = cursor.fetchall()
    
    print(f"Discovering en {len(nodes)} nodos con {workers} workers...")
    
    found_total = 0
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(discover_node, n): n for n in nodes}
        for future in as_completed(futures):
            ip, urls = future.result()
            for url in urls:
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO streams (url, channel, country, node_ip, status)
                        VALUES (?, ?, ?, ?, 'unknown')
                    """, (url, "discovered", "unknown", ip))
                    found_total += 1
                except:
                    pass
    
    conn.commit()
    print(f"✔ {found_total} nuevos streams descubiertos")

if __name__ == '__main__':
    discover(100, 30)