import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

NEW_IPS = [
    ("138.117.86.160", 18000),
    ("138.117.86.162", 18000),
    ("138.117.86.165", 18000),
    ("138.117.86.167", 18000),
    ("138.117.86.170", 18000),
    ("138.117.86.171", 18000),
    ("138.117.86.174", 18000),
    ("181.205.130.194", 4000),
    ("170.239.205.81", 8000),
    ("181.174.228.40", 8000),
    ("190.66.24.164", 45000),
    ("201.219.223.99", 45000),
    ("201.182.249.99", 4021),
    ("181.66.249.246", 8000),
    ("45.177.21.6", 8000),
    ("179.63.6.12", 8000),
    ("186.148.196.67", 8000),
    ("200.59.188.3", 8000),
    ("45.169.163.237", 8000),
    ("176.65.146.224", 8000),
    ("109.245.49.186", 8000),
    ("38.41.8.1", 8000),
    ("38.137.192.250", 8000),
    ("38.7.223.20", 8000),
    ("45.189.151.7", 8000),
    ("190.61.40.187", 45000),
    ("190.61.43.121", 45000),
    ("190.61.43.123", 45000),
    ("200.95.184.125", 8000),
    ("201.218.140.30", 8000),
    ("181.78.12.164", 9000),
    ("181.78.74.146", 18000),
    ("181.78.74.226", 18000),
]

PATHS = [
    "play/a01", "play/a02", "play/a03", "play/a04", "play/a05",
    "play/a06", "play/a07", "play/a08", "play/a09", "play/a0a",
    "play/a0b", "play/a0c", "play/a0d", "play/a0e", "play/a0f",
    "play/a0g", "play/a0h", "play/a0i", "play/a0j",
    "play/a0k", "play/a0l", "play/a0m", "play/a0n", "play/a0o",
    "play/index.m3u8", "live/index.m3u8", "playlist.m3u8",
    "live/playlist.m3u8", "stream/playlist.m3u8",
    "stream/1/index.m3u8", "hls/playlist.m3u8",
    "tv/playlist.m3u8", "direct/playlist.m3u8",
]

def scan_ip(ip, port):
    base = f"http://{ip}:{port}"
    found = []
    
    for path in PATHS:
        url = f"{base}/{path}"
        try:
            r = requests.head(url, timeout=2, allow_redirects=True)
            if r.status_code == 200:
                found.append(url)
        except:
            pass
    
    return ip, port, found

def discover_new_ips(workers=20):
    print(f"Escaneando {len(NEW_IPS)} IPs...")
    
    results = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(scan_ip, ip, port): (ip, port) for ip, port in NEW_IPS}
        
        for future in as_completed(futures):
            ip, port, found = future.result()
            if found:
                print(f"  {ip}:{port} -> {len(found)} paths")
                results.append((ip, port, found))
    
    return results

def save_to_db(results):
    from db import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    
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
    print(f"Guardados {total} nuevos streams")
    return total

if __name__ == '__main__':
    results = discover_new_ips()
    if results:
        save_to_db(results)