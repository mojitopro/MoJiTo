#!/usr/bin/env python3
"""
Intelligent Stream Analyzer
Analiza video real, no solo conexiones
"""
import json
import requests
import time
import re
import subprocess
import os

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (SMART-TV) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': '*/*',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Referer': 'https://mojitopro.github.io/'
}

def parse_hls_manifest(url, timeout=5):
    """Parse HLS manifest y obtener info de calidad"""
    try:
        r = requests.get(url, timeout=timeout, headers=HEADERS)
        if r.status_code != 200:
            return None, 'http_error'
        
        content = r.text
        
        # Buscar resolutions en el manifeste
        resolutions = []
        for line in content.split('\n'):
            if 'RESOLUTION=' in line:
                match = re.search(r'RE?SOLUTION=(\d+)x(\d+)', line)
                if match:
                    w, h = match.groups()
                    resolutions.append(f"{w}x{h}")
        
        # Contar segmentos
        segments = [l for l in content.split('\n') if l and not l.startswith('#')]
        
        return {
            'type': 'hls',
            'resolutions': resolutions,
            'segments': len(segments),
            'bandwidth': re.findall(r'BANDWIDTH=(\d+)', content)
        }, None
        
    except Exception as e:
        return None, str(e)[:30]

def test_direct_stream(url, timeout=8):
    """Test stream directo - descargar chunks y analizar"""
    result = {
        'url': url,
        'type': 'unknown',
        'ok': False,
        'issues': [],
        'data_received': 0,
        'first_byte_ms': 0,
        'buffer_ms': 0
    }
    
    try:
        start = time.time()
        
        # Request con Range para solo headers primero
        r = requests.get(url, headers={**HEADERS, 'Range': 'bytes=0-0'}, timeout=3, stream=True)
        
        if r.status_code not in [200, 206]:
            result['issues'].append(f"HTTP {r.status_code}")
            return result
        
        # Headers del servidor
        result['server'] = r.headers.get('Server', '')[:30]
        ct = r.headers.get('Content-Type', '')
        
        # Detectar tipo
        if '.m3u8' in url:
            result['type'] = 'hls_manifest'
        elif 'video' in ct or 'mp4' in ct:
            result['type'] = 'video/mp4'
        elif ct:
            result['type'] = ct.split(';')[0][:20]
        
        result['first_byte_ms'] = int((time.time() - start) * 1000)
        
        # Recibir datos reales
        bytes_received = 0
        chunks = 0
        chunk_times = []
        
        try:
            for chunk in r.iter_content(chunk_size=32768, timeout=timeout):
                if chunk:
                    bytes_received += len(chunk)
                    chunks += 1
                    if chunks == 1:
                        result['buffer_ms'] = int((time.time() - start) * 1000)
                    
                    if bytes_received > 500000:  # 500KB suficiente para verificar
                        break
                        
        except requests.exceptions.Timeout:
            result['issues'].append(f"timeout_after_{bytes_received}")
        except Exception as e:
            result['issues'].append(str(e)[:20])
        
        result['data_received'] = bytes_received
        result['chunks_received'] = chunks
        
        # Evaluar
        if bytes_received > 100000:  # Al menos 100KB
            result['ok'] = True
        
    except requests.exceptions.Timeout:
        result['issues'].append('timeout')
    except requests.exceptions.ConnectionError:
        result['issues'].append('connection_error')
    except Exception as e:
        result['issues'].append(str(e)[:30])
    
    return result

def test_stream(url):
    """Test inteligente de cualquier stream"""
    # Si es HLS, parsear manifest
    if '.m3u8' in url:
        hls_info, error = parse_hls_manifest(url)
        if hls_info:
            return {
                'url': url,
                'type': 'hls',
                'ok': True,
                'hls_info': hls_info
            }
    
    # Test directo
    return test_direct_stream(url)

def test_all_streams():
    """Testear todos los canales"""
    with open('premium_consolidated.json') as f:
        data = json.load(f)
    
    results = []
    
    print(f"Testing {len(data['channels'])} canales con video real...\n")
    
    for i, ch in enumerate(data['channels'], 1):
        name = ch['name']
        url = ch.get('url', '')
        fallbacks = ch.get('fallbacks', [])
        
        all_urls = [url] + fallbacks
        
        best_result = None
        
        for u in all_urls:
            if not u:
                continue
            
            print(f"[{i}/{len(data['channels'])}] {name}...", end=' ')
            result = test_stream(u)
            
            if result.get('ok'):
                print(f"OK ({result.get('type')})")
                best_result = result
                break
            else:
                issues = result.get('issues', ['unknown'])
                print(f"FAIL: {issues[0] if issues else 'no_data'}")
        
        if best_result:
            results.append({
                'channel': name,
                'type': best_result.get('type'),
                'ok': True,
                'data': best_result.get('data_received', 0),
                'buffer_ms': best_result.get('buffer_ms', 0)
            })
    
    # Guardar
    with open('intelligent_report.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    working = [r for r in results if r.get('ok')]
    
    print(f"\n=== RESUMEN INTELIGENTE ===")
    print(f"Total: {len(data['channels'])}")
    print(f"Video real recibido: {len(working)}")
    
    # Por tipo
    by_type = {}
    for r in results:
        t = r.get('type', 'unknown')
        by_type[t] = by_type.get(t, 0) + 1
    
    print(f"\nPor tipo:")
    for t, c in by_type.items():
        print(f"  {t}: {c}")
    
    print(f"\nGuardado: intelligent_report.json")

if __name__ == '__main__':
    test_all_streams()