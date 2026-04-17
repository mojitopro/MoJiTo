#!/usr/bin/env python3
"""
Stream Quality Tester - Simple
Solo verifica HTTP status y Content-Type
"""
import json
import requests
from collections import defaultdict
import time

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (SMART-TV) AppleWebKit/537.36',
    'Accept': '*/*',
    'Connection': 'keep-alive'
}

def test_simple(url, timeout=4):
    """Test simple sin analizar contenido"""
    try:
        start = time.time()
        r = requests.get(url, timeout=timeout, allow_redirects=True, headers=HEADERS)
        elapsed = time.time() - start
        
        server = r.headers.get('Server', '')[:30]
        content_type = r.headers.get('Content-Type', '')[:50]
        length = r.headers.get('Content-Length', '')
        
        return {
            'url': url,
            'final_url': r.url,
            'status': r.status_code,
            'time_ms': int(elapsed * 1000),
            'server': server,
            'content_type': content_type,
            'length': length,
            'ok': r.status_code in [200, 206]
        }
    except requests.exceptions.Timeout:
        return {'url': url, 'status': 0, 'ok': False, 'error': 'timeout'}
    except requests.exceptions.ConnectionError:
        return {'url': url, 'status': 0, 'ok': False, 'error': 'connection'}
    except Exception as e:
        return {'url': url, 'status': 0, 'ok': False, 'error': str(e)[:30]}

def test_all():
    with open('premium_consolidated.json') as f:
        data = json.load(f)
    
    results = []
    working = []
    
    for ch in data['channels']:
        name = ch['name']
        url = ch.get('url', '')
        fallbacks = ch.get('fallbacks', [])
        
        all_urls = [url] + fallbacks
        
        best = None
        for u in all_urls:
            if not u:
                continue
            result = test_simple(u)
            if result.get('ok'):
                best = result
                break
        
        if best:
            working.append({
                'name': name,
                'url': best['url'],
                'server': best.get('server', ''),
                'type': best.get('content_type', '')
            })
            print(f"✓ {name}: {best['server']} ({best['time_ms']}ms)")
        else:
            # Test fallbacks para ver error
            for u in all_urls[:1]:
                if u:
                    result = test_simple(u)
                    status_code = result.get('status', 'N/A')
                    print(f"✗ {name}: HTTP {status_code}")
        
        results.append({'channel': name, 'streams': [test_simple(u) for u in all_urls if u]})
    
    # Save working
    with open('working_streams.json', 'w') as f:
        json.dump(working, f, indent=2)
    
    print(f"\n=== RESUMEN ===")
    print(f"Total: {len(data['channels'])}")
    print(f"Working: {len(working)}")
    print(f"Guardado: working_streams.json")

if __name__ == '__main__':
    test_all()