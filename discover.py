import requests
import sqlite3
import os
from db import get_connection

PATHS = [
    "play/a01", "play/a02", "play/a03", "play/a04", "play/a05",
    "play/a06", "play/a07", "play/a08", "play/a09", "play/a10",
    "play/a0a", "play/a0b", "play/a0c", "play/a0d", "play/a0e",
    "play/index.m3u8", "live/playlist.m3u8", "live/index.m3u8"
]

def discover(limit=50):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT ip, port FROM nodes LIMIT ?", (limit,))
    nodes = cursor.fetchall()
    
    print(f"Discovering en {len(nodes)} nodos...")
    
    found = 0
    for node in nodes:
        ip, port = node['ip'], node['port']
        base = f"http://{ip}:{port}"
        
        for p in PATHS:
            url = f"{base}/{p}"
            try:
                r = requests.head(url, timeout=2, allow_redirects=True)
                if r.status_code == 200:
                    cursor.execute("""
                        INSERT OR IGNORE INTO streams (url, channel, country, node_ip, status)
                        VALUES (?, ?, ?, ?, 'unknown')
                    """, (url, "discovered", "unknown", ip))
                    found += 1
            except:
                pass
    
    conn.commit()
    print(f"✔ {found} nuevos streams descubiertos")

if __name__ == '__main__':
    discover(20)