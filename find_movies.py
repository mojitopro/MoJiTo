#!/usr/bin/env python3
import requests
import json
import subprocess
import re
from collections import defaultdict

CANALES_OBJETIVO = ['HBO', 'ESPN', 'ADULT SWIM', 'TNT', 'SPACE', 'GOLDEN', 'STAR', 
                   'PARAMOUNT', 'AMC', 'UNIVERSAL', 'FX', 'SONY', 'AXN', 'CINEMAX',
                   'TBS', 'COMEDY CENTRAL', 'DISCOVERY', 'NAT GEO', 'DISNEY', 'NICKELODEON']

FUENTES = [
    "https://iptv.org/regions/latam.m3u",
    "https://iptv.org/countries/co.m3u",
    "https://iptv.org/countries/mx.m3u",
    "https://iptv.org/countries/ar.m3u",
    "https://iptv.org/countries/ve.m3u",
    "https://iptv.org/countries/pe.m3u",
    "https://iptv.org/countries/cl.m3u",
]

all_found = defaultdict(list)

for fuente in FUENTES:
    try:
        r = requests.get(fuente, timeout=15)
        if r.status_code == 200:
            lines = r.text.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('#EXTINF:'):
                    match = re.search(r'tvg-name="([^"]+)"', line)
                    if match:
                        nombre = match.group(1).upper()
                        for objetivo in CANALES_OBJETIVO:
                            if objetivo in nombre:
                                if i+1 < len(lines) and lines[i+1].startswith('http'):
                                    url = lines[i+1].strip()
                                    all_found[objetivo].append(url)
    except:
        pass

print("Por canal:")
for canal, urls in all_found.items():
    print(f" {canal}: {len(urls)}")

WORKING = []
for canal, urls in all_found.items():
    print(f"Test {canal}...", end=" ")
    ok = False
    for url in urls[:15]:
        try:
            r = subprocess.run(['curl', '-sI', '--max-time', '4', url], 
                            capture_output=True, text=True, timeout=5)
            if '200' in r.stdout or '301' in r.stdout:
                WORKING.append({'name': canal, 'url': url, 'backups': urls[:8], 'category': 'Peliculas'})
                print("OK")
                ok = True
                break
        except:
            pass
    if not ok:
        print("NO")

with open('custom_channels.json', 'w') as f:
    json.dump(WORKING, f, indent=2)

print(f"\nTotal: {len(WORKING)} canales guardados")