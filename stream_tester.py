#!/usr/bin/env python3
"""
Stream Quality Tester - MoJiTo
Verifica streams por consumo real de video, no solo HTTP
"""
import json
import time
import requests
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

HEADERS = {'User-Agent': 'Mozilla/5.0', 'Range': 'bytes=0-1024'}

def test_stream_basic(url, timeout=3):
    """Test básico de conexión"""
    try:
        start = time.time()
        r = requests.head(url, timeout=timeout, headers=HEADERS)
        elapsed = time.time() - start
        return {
            'url': url,
            'status': r.status_code,
            'time': elapsed,
            'ok': r.status_code == 200
        }
    except Exception as e:
        return {'url': url, 'status': 0, 'time': 0, 'ok': False, 'error': str(e)[:50]}

def analyze_server(url):
    """Analiza el servidor de streaming"""
    result = {'url': url, 'server': 'unknown', 'type': 'unknown'}
    
    try:
        r = requests.head(url, timeout=3, headers=HEADERS)
        server = r.headers.get('Server', '')
        
        if 'nginx' in server.lower():
            result['server'] = 'nginx'
        elif 'Astra' in server:
            result['server'] = 'astra'
        elif 'hls' in url.lower() or '.m3u8' in url:
            result['server'] = 'hls'
            result['type'] = 'hls'
        elif 'mpeg-dash' in url.lower():
            result['server'] = 'dash'
            result['type'] = 'dash'
        else:
            result['server'] = server[:20] if server else 'unknown'
            
        # Check content-type
        ct = r.headers.get('Content-Type', '')
        if 'video' in ct:
            result['type'] = 'video'
        elif 'mpegurl' in ct or 'application/vnd' in ct:
            result['type'] = 'hls'
            
    except Exception as e:
        result['error'] = str(e)[:30]
    
    return result

def test_stream_quality(url, timeout=5):
    """Test completo de stream"""
    result = {
        'url': url,
        'connect_time': 0,
        'server': 'unknown',
        'type': 'unknown',
        'ok': False,
        'issues': []
    }
    
    try:
        start = time.time()
        
        # Test 1: Conexión
        r = requests.get(url, stream=True, timeout=timeout, headers={'Range': 'bytes=0-0'})
        result['connect_time'] = time.time() - start
        
        if r.status_code not in [200, 206]:
            result['issues'].append(f'HTTP {r.status_code}')
            return result
            
        # Analizar servidor
        server = r.headers.get('Server', '')
        result['server'] = server[:30] if server else 'unknown'
        
        # Detectar tipo
        if '.m3u8' in url:
            result['type'] = 'hls'
        elif '.mpd' in url:
            result['type'] = 'dash'
        elif 'video' in r.headers.get('Content-Type', ''):
            result['type'] = 'direct'
        else:
            result['type'] = 'unknown'
            
        # Test 2: Recibir datos
        try:
            data = next(r.iter_content(chunk_size=8192, timeout=2))
            if data and len(data) > 0:
                result['ok'] = True
                result['size'] = len(data)
        except:
            result['issues'].append('no_data')
            
    except requests.exceptions.Timeout:
        result['issues'].append('timeout')
    except requests.exceptions.ConnectionError:
        result['issues'].append('connection_error')
    except Exception as e:
        result['issues'].append(str(e)[:30])
    
    return result

def test_channel_streams(channel_name, urls):
    """Prueba todos los streams de un canal"""
    results = []
    
    for url in urls:
        if not url or url == 'unknown':
            continue
            
        # Test básico
        basic = test_stream_basic(url)
        
        # Análisis de servidor
        server_info = analyze_server(url)
        
        # Test de calidad
        quality = test_stream_quality(url)
        
        results.append({
            'url': url,
            'ok': basic['ok'] and quality.get('ok', False),
            'connect_ms': int(basic['time'] * 1000),
            'server': server_info['server'],
            'type': quality.get('type', 'unknown'),
            'quality': quality
        })
    
    # Ordenar por calidad
    results.sort(key=lambda x: (
        x.get('ok', False),
        0 if x.get('server') == 'unknown' else 1,
        x.get('connect_ms', 9999)
    ), reverse=True)
    
    return {
        'channel': channel_name,
        'streams': results,
        'best': results[0] if results else None
    }

def test_all_channels(channels_file='premium_consolidated.json'):
    """Prueba todos los canales"""
    import sqlite3
    
    # Cargar canales
    with open(channels_file) as f:
        data = json.load(f)
    
    # Agrupar por nombre de canal
    by_name = defaultdict(list)
    
    for ch in data['channels']:
        name = ch['name']
        url = ch.get('url', '')
        by_name[name].append(url)
        
        for fb in ch.get('fallbacks', []):
            if fb:
                by_name[name].append(fb)
    
    # Testear grupos
    results = []
    
    print(f"Testing {len(by_name)} canales...")
    
    for i, (name, urls) in enumerate(by_name.items(), 1):
        print(f"[{i}/{len(by_name)}] {name}...", end=' ')
        
        result = test_channel_streams(name, urls)
        
        if result['best'] and result['best'].get('ok'):
            print(f"OK ({result['best'].get('type')} - {result['best'].get('server')})")
        else:
            print("FAIL")
            
        results.append(result)
    
    # Guardar resultados
    with open('stream_quality_report.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    # Resumen
    total = len(results)
    working = sum(1 for r in results if r.get('best', {}).get('ok'))
    
    print(f"\n=== RESUMEN ===")
    print(f"Total canales: {total}")
    print(f"Con al menos 1 stream: {len([r for r in results if r['streams']])}")
    print(f"Streams funcionales: {working}")
    print(f"Guardado en: stream_quality_report.json")
    
    return results

def analyze_best_streams():
    """Analiza los mejores streams por categoría"""
    with open('stream_quality_report.json') as f:
        data = json.load(f)
    
    by_type = defaultdict(list)
    by_server = defaultdict(list)
    
    for ch in data:
        best = ch.get('best')
        if best and best.get('ok'):
            by_type[best.get('type', 'unknown')].append(ch['channel'])
            by_server[best.get('server', 'unknown')].append(ch['channel'])
    
    print("\n=== MEJORES POR TIPO ===")
    for t, chs in by_type.items():
        print(f"{t}: {len(chs)} canales")
    
    print("\n=== MEJORES POR SERVIDOR ===")
    for s, chs in by_server.items():
        print(f"{s}: {len(chs)} canales")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'analyze':
        analyze_best_streams()
    else:
        test_all_channels()