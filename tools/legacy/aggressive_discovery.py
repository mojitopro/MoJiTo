import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import sqlite3
import os
from db_utils import get_db_path

def generate_paths():
    paths = []
    
    # play/a01 through play/a99 and play/a0a through play/a0z
    for i in range(1, 100):
        paths.append(f"play/a{i:02d}")
        paths.append(f"play/{i:03d}")
    
    for i in range(0, 256):
        paths.append(f"play/a{i:02x}")
        paths.append(f"play/{i:03x}")
    
    # Common m3u8 paths
    paths.extend([
        "play/index.m3u8", "live/index.m3u8", "playlist.m3u8",
        "live/playlist.m3u8", "stream/playlist.m3u8", "hls/playlist.m3u8",
        "live/live.m3u8", "stream.m3u8", "index.m3u8",
    ])
    
    return paths

def scan_ip_paths(ip, port, paths):
    base = f"http://{ip}:{port}"
    found = []
    
    for path in paths:
        url = f"{base}/{path}"
        try:
            r = requests.head(url, timeout=1, allow_redirects=True)
            if r.status_code == 200:
                found.append(url)
        except:
            pass
    
    return ip, port, found

def aggressive_discovery():
    DB_PATH = get_db_path()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all unique IPs
    cursor.execute('SELECT DISTINCT node_ip FROM streams WHERE node_ip IS NOT NULL')
    ips = [r[0] for r in cursor.fetchall() if r[0]]
    
    # Also get from nodes table
    cursor.execute('SELECT ip, port FROM nodes')
    nodes = cursor.fetchall()
    
    # Combine unique IPs
    all_ips = set(ips)
    for ip, port in nodes:
        all_ips.add(ip)
    
    print(f"Descubriendo en {len(all_ips)} IPs...")
    
    paths = generate_paths()
    print(f"Probando {len(paths)} paths por IP...")
    
    results = []
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = []
        for ip in all_ips:
            # Common ports
            for port in [8000, 8080, 9000, 18000, 45000, 4000, 4021, 7000]:
                futures.append(executor.submit(scan_ip_paths, ip, port, paths))
        
        done = 0
        for future in as_completed(futures):
            try:
                ip, port, found = future.result()
                if found:
                    print(f"  {ip}:{port} -> {len(found)}")
                    results.append((ip, port, found))
            except:
                pass
            done += 1
            if done % 50 == 0:
                print(f"  Progreso: {done}/{len(futures)}")
    
    # Save to DB
    total = 0
    for ip, port, urls in results:
        for url in urls:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO streams (url, channel, status, node_ip)
                    VALUES (?, ?, 'unknown', ?)
                """, (url, "discovered", ip))
                total += 1
            except:
                pass
    
    conn.commit()
    print(f"\nTotal nuevos streams: {total}")

if __name__ == '__main__':
    aggressive_discovery()
