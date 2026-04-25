#!/usr/bin/env python3
"""Quick verify Adult Swim + Peliculas - fast version"""
import urllib.request
import json
import subprocess
import sys

HEADERS = {'User-Agent': 'Mozilla/5.0 (SMART-TV)'}

def quick_check(url):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        resp = urllib.request.urlopen(req, timeout=8)
        if resp.status != 200:
            return {'http': resp.status, 'video': False, 'error': f'HTTP {resp.status}'}
        
        cmd = ['ffmpeg', '-y', '-i', url, '-t', '2', '-vf', 'fps=1,scale=80:45', '-f', 'mjpeg', '-']
        result = subprocess.run(cmd, capture_output=True, timeout=12)
        
        if result.returncode != 0:
            return {'http': 200, 'video': False, 'error': 'ffmpeg fail'}
        
        if len(result.stdout) < 500:
            return {'http': 200, 'video': False, 'error': 'no frame'}
        
        return {'http': 200, 'video': True, 'bytes': len(result.stdout)}
    except Exception as e:
        return {'http': 0, 'video': False, 'error': str(e)[:50]}

def main():
    targets = [
        ('Adult Swim', 'http://190.60.59.67:8000/play/a0io'),
        ('Adult Swim', 'http://181.119.86.1:8000/play/a019'),
        ('Adult Swim', 'http://190.61.42.218:9000/play/a06r'),
        ('Adult Swim', 'http://181.78.79.131:8000/play/a0pk'),
        ('TNT', 'http://38.41.8.1:8000/play/a0sv'),
        ('Space', 'http://38.41.8.1:8000/play/a0rm'),
        ('Cinecanal', 'http://38.41.8.1:8000/play/a0sx'),
        ('Golden', 'http://38.41.8.1:8000/play/a0zx'),
        ('Golden Edge', 'http://38.41.8.1:8000/play/a0t7'),
        ('Studio Universal', 'http://38.41.8.1:8000/play/a0rp'),
        ('TBS', 'http://38.41.8.1:8000/play/a0sw'),
        ('HBO', 'http://45.181.120.65:9087/play/128/index.m3u8'),
    ]
    
    working = []
    failed = []
    
    for name, url in targets:
        print(f"Testing {name}...", end=" ")
        sys.stdout.flush()
        result = quick_check(url)
        print(f"HTTP:{result['http']} Video:{result['video']}", end="")
        if result['video']:
            print(f" ({result.get('bytes',0)} bytes)")
            working.append({'name': name, 'url': url, 'bytes': result.get('bytes', 0)})
        else:
            print(f" - {result.get('error','')}")
            failed.append({'name': name, 'url': url, 'error': result.get('error','')})
    
    print(f"\n=== RESULTS ===")
    print(f"Working: {len(working)}")
    for w in working:
        print(f"  ✓ {w['name']}: {w['url']}")
    print(f"\nFailed: {len(failed)}")
    for f in failed:
        print(f"  ✗ {f['name']}: {f['error']}")
    
    with open('/data/data/com.termux/files/home/MoJiTo/verified_critical.json', 'w') as f:
        json.dump({'working': working, 'failed': failed}, f, indent=2)

if __name__ == '__main__':
    main()