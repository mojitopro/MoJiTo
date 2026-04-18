#!/usr/bin/env python3
import socket
import requests
import concurrent.futures
import json
import time

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

KNOWN_SERVERS = [
    ('181.78.78.66', 8000),
    ('181.78.79.131', 8000),
    ('181.119.86.1', 8000),
    ('186.148.175.138', 8000),
    ('186.96.98.138', 19000),
    ('190.13.81.221', 18000),
    ('138.117.86.160', 18000),
    ('138.117.86.162', 18000),
    ('138.117.86.165', 18000),
    ('138.117.86.167', 18000),
    ('138.117.86.170', 18000),
    ('138.117.86.171', 18000),
    ('138.117.86.174', 18000),
    ('45.169.163.237', 4000),
    ('179.63.6.12', 9000),
    ('181.66.249.246', 8000),
    ('45.177.21.6', 9000),
    ('170.239.205.81', 30000),
    ('176.65.146.224', 5007),
    ('181.78.12.164', 9000),
    ('181.78.74.146', 18000),
    ('181.78.74.226', 45000),
    ('181.174.228.40', 8000),
    ('181.205.130.194', 4000),
    ('186.148.196.67', 8800),
    ('190.60.37.118', 4000),
    ('190.60.59.67', 8000),
    ('190.61.40.187', 45000),
    ('190.61.42.218', 9000),
    ('190.61.43.121', 45000),
    ('190.61.43.123', 45000),
    ('190.66.24.164', 45000),
    ('200.59.188.3', 8000),
    ('200.95.184.125', 8450),
    ('201.182.249.99', 4021),
    ('201.218.140.30', 9000),
    ('201.219.223.99', 45000),
    ('109.245.49.186', 8000),
    ('38.41.8.1', 8000),
    ('38.137.192.250', 8000),
    ('38.7.223.20', 8000),
    ('45.189.151.7', 8000),
]

PORTS = [8000, 8001, 8080, 8443, 18000, 19000, 30000, 40000, 45000, 25461]

STREAM_IDS = []
for i in range(1, 500):
    STREAM_IDS.extend([
        f"a{i:03d}",
        f"a{i:04d}",
        f"0{i:05d}",
        f"{i}",
    ])

def check_port(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex((ip, port))
    sock.close()
    return result == 0

def get_panel_info(ip, port):
    try:
        url = f"http://{ip}:{port}/"
        r = requests.get(url, timeout=5, headers=HEADERS)
        server = r.headers.get('Server', '')
        
        data = {
            'ip': ip,
            'port': port,
            'status': r.status_code,
            'server': server,
            'title': '',
        }
        
        if 'Astra' in server:
            data['type'] = 'astra'
            
            api_urls = [
                f"http://{ip}:{port}/panel_api.php",
                f"http://{ip}:{port}/player_api.php",
                f"http://{ip}:{port}/stalker_portal/server_load",
            ]
            
            for api_url in api_urls:
                try:
                    ar = requests.get(api_url, timeout=3, headers=HEADERS)
                    if ar.status_code == 200:
                        data['api'] = api_url
                        break
                except:
                    pass
                    
        return data
    except Exception as e:
        return None

def get_streams_from_api(ip, port):
    streams = []
    
    apis = [
        f"http://{ip}:{port}/player_api.php",
        f"http://{ip}:{port}/panel_api.php?action=get_streams",
    ]
    
    for api_url in apis:
        try:
            r = requests.get(api_url, timeout=5, headers=HEADERS)
            if r.status_code == 200:
                try:
                    data = r.json()
                    
                    if 'streams' in data:
                        for s in data['streams']:
                            streams.append({
                                'name': s.get('name', ''),
                                'stream_id': s.get('stream_id', ''),
                                'url': f"http://{ip}:{port}/{s.get('stream_id', '')}",
                            })
                    elif 'data' in data:
                        for s in data['data']:
                            streams.append({
                                'name': s.get('name', ''),
                                'stream_id': s.get('stream_id', ''),
                                'url': f"http://{ip}:{port}/{s.get('stream_id', '')}",
                            })
                    elif 'available_channels' in data:
                        for name, info in data['available_channels'].items():
                            streams.append({
                                'name': name,
                                'stream_id': info.get('id', ''),
                            })
                            
                    if streams:
                        break
                except:
                    pass
        except:
            pass
    
    if not streams:
        for sid in STREAM_IDS[:100]:
            test_urls = [
                f"http://{ip}:{port}/play/{sid}",
                f"http://{ip}:{port}/live/{sid}/{sid}.m3u8",
                f"http://{ip}:{port}/stream/{sid}.m3u8",
            ]
            
            for test_url in test_urls:
                try:
                    r = requests.head(test_url, timeout=1, headers=HEADERS)
                    if r.status_code == 200:
                        ct = r.headers.get('Content-Type', '')
                        if 'video' in ct or 'mpeg' in ct or 'octet' in ct or '200' in str(r.status_code):
                            streams.append({
                                'name': f"Stream_{sid}",
                                'stream_id': sid,
                                'url': test_url,
                            })
                except:
                    pass
    
    return streams

def scan_server(ip, port):
    print(f"[*] Scanning {ip}:{port}...")
    
    result = {
        'ip': ip,
        'port': port,
        'alive': False,
        'type': '',
        'streams': [],
    }
    
    if check_port(ip, port):
        result['alive'] = True
        print(f"  [!] Port {port} is OPEN")
        
        panel = get_panel_info(ip, port)
        if panel:
            result['type'] = panel.get('type', 'unknown')
            
            print(f"  [*] Getting streams...")
            streams = get_streams_from_api(ip, port)
            result['streams'] = streams
            print(f"  -> Found {len(streams)} streams")
    
    return result

def main():
    print("=== Server Stream Scanner ===")
    print(f"[*] Scanning {len(KNOWN_SERVERS)} servers...\n")
    
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(scan_server, ip, port) for ip, port in KNOWN_SERVERS]
        
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result['alive']:
                results.append(result)
                
                if result['streams']:
                    print(f"  [!] {result['ip']}:{result['port']} - {len(result['streams'])} streams\n")
    
    active = sum(1 for r in results if r['alive'])
    with_streams = sum(1 for r in results if r['streams'])
    total_streams = sum(len(r['streams']) for r in results)
    
    print(f"\n=== Results ===")
    print(f"Active servers: {active}/{len(KNOWN_SERVERS)}")
    print(f"Servers with streams: {with_streams}")
    print(f"Total streams: {total_streams}")
    
    out_file = '/data/data/com.termux/files/home/MoJiTo/streams_scanned.json'
    with open(out_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n[+] Saved to {out_file}")

if __name__ == '__main__':
    main()