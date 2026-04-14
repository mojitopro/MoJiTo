import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

PATHS = []

# Generate play/a01 through play/a99
for i in range(1, 100):
    PATHS.append(f"play/a{i:02d}")
    PATHS.append(f"play/a{i:02x}")

# Common m3u8 paths
PATHS.extend([
    "play/index.m3u8", "live/index.m3u8", "playlist.m3u8",
    "live/playlist.m3u8", "stream/playlist.m3u8",
    "stream/1/index.m3u8", "hls/playlist.m3u8",
    "tv/playlist.m3u8", "direct/playlist.m3u8",
    "live/live.m3u8", "hls/live.m3u8",
    "stream.m3u8", "live.m3u8", "index.m3u8",
    "channel/playlist.m3u8", "tv/channels.m3u8",
    "streams/playlist.m3u8", "udp/playlist.m3u8",
])

def scan_all_paths(ip, port):
    base = f"http://{ip}:{port}"
    found = []
    
    for path in PATHS:
        url = f"{base}/{path}"
        try:
            r = requests.head(url, timeout=1.5, allow_redirects=True)
            if r.status_code == 200:
                found.append(url)
        except:
            pass
    
    return ip, port, found

def discover_ip(ip, port):
    print(f"Escaneando {ip}:{port}...")
    ip, port, found = scan_all_paths(ip, port)
    if found:
        print(f"  -> {len(found)} streams encontrados")
    return ip, port, found

def discover_all():
    from db import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get all unique IPs from existing streams
    cursor.execute("SELECT DISTINCT ip, port FROM nodes")
    nodes = cursor.fetchall()
    
    print(f"Escaneando {len(nodes)} nodos...")
    
    all_results = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(discover_ip, n[0], n[1]): n for n in nodes}
        
        for future in as_completed(futures):
            try:
                ip, port, found = future.result()
                if found:
                    all_results.append((ip, port, found))
            except:
                pass
    
    # Save to DB
    total = 0
    for ip, port, urls in all_results:
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
    discover_all()