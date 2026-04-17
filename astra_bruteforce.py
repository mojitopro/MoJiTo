#!/usr/bin/env python3
import socket
import requests
import concurrent.futures
import random
import time

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

PORTS = [8000, 8001, 8080, 8443, 18000, 19000, 30000, 40000, 45000]
COUNTRIES = {
    'CO': range(181, 255),
    'PE': range(181, 255),
    'VE': range(200, 212),
    'CL': range(200, 212),
    'MX': range(189, 195),
    'AR': range(200, 212),
    'BR': range(200, 212),
    'US': range(1, 256),
    'ES': range(87, 92),
    'FR': range(80, 92),
    'DE': range(80, 92),
}

def check_astra(ip, port):
    try:
        url = f"http://{ip}:{port}/"
        r = requests.get(url, timeout=3, headers=HEADERS)
        server = r.headers.get('Server', '')
        if 'Astra' in server or 'nginx' in server or r.status_code == 200:
            return (ip, port, r.status_code, server)
    except:
        pass
    return None

def get_stream_url(ip, port, stream_id):
    return f"http://{ip}:{port}/play/{stream_id}"

def generate_stream_ids():
    ids = []
    for i in range(1, 1000):
        ids.append(f"a{i:03d}")
        ids.append(f"a{i:04d}")
        ids.append(f"a{i:05d}")
        ids.append(f"0{i:04d}")
    return ids

def scan_ip(ip_port):
    ip, port = ip_port
    return check_astra(ip, port)

def scan_country_range(country, sample_size=500):
    results = []
    prefix = COUNTRIES.get(country, [random.randint(1, 223)])
    
    ip_list = []
    for b in list(prefix)[:10]:
        for c in list(range(1, 256))[:20]:
            for d in list(range(1, 256))[:50]:
                ip_list.append(f"190.{b}.{c}.{d}")
    
    if not ip_list:
        return results
    
    ip_list = random.sample(ip_list, min(sample_size, len(ip_list)))
    
    targets = [(ip, port) for ip in ip_list for port in PORTS]
    
    print(f"[{country}] Scanning {len(targets)} targets...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        futures = {executor.submit(scan_ip, t): t for t in targets}
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                results.append(result)
                print(f"[!] FOUND: {result[0]}:{result[1]} ({result[3]})")
    
    return results

def scan_known_servers():
    known = [
        ('181.78.78.66', 8000),
        ('181.78.79.131', 8000),
        ('181.119.86.1', 8000),
        ('186.148.175.138', 8000),
        ('186.96.98.138', 19000),
        ('190.13.81.221', 18000),
        ('138.117.86.160', 18000),
        ('138.117.86.162', 18000),
        ('45.169.163.237', 4000),
        ('179.63.6.12', 9000),
    ]
    
    results = []
    print("[*] Scanning known servers...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(check_astra, ip, port) for ip, port in known]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                results.append(result)
                print(f"[!] FOUND: {result[0]}:{result[1]} ({result[3]})")
    
    return results

def find_streams(ip, port, num_streams=100):
    stream_urls = []
    stream_ids = generate_stream_ids()
    stream_ids = random.sample(stream_ids, min(num_streams, len(stream_ids)))
    
    print(f"[*] Checking streams on {ip}:{port}...")
    
    for sid in stream_ids[:50]:
        url = f"http://{ip}:{port}/play/{sid}"
        try:
            r = requests.head(url, timeout=2, headers=HEADERS)
            if r.status_code == 200:
                content_type = r.headers.get('Content-Type', '')
                print(f"  [!] STREAM: {url} ({content_type})")
                stream_urls.append(url)
        except:
            pass
    
    return stream_urls

def brute_ports(ip, ports=[8000, 8001, 8080, 8443, 18000, 19000, 30000, 40000, 45000]):
    results = []
    for port in ports:
        result = check_astra(ip, port)
        if result:
            results.append(result)
    return results

if __name__ == '__main__':
    print("=== Astra IPTV Brute Force Scanner ===")
    
    results = scan_known_servers()
    print(f"\n[*] Found {len(results)} active servers")
    
    if results:
        for ip, port, code, server in results[:5]:
            streams = find_streams(ip, port, 50)
            print(f"  -> {len(streams)} streams found")