#!/usr/bin/env python3
import time
import os
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

from scraper.searchtv import search
from core.cache import get_cached, set_cached, get_fallback
from selector import get_best_stream, get_all_channels
from db import get_connection

def get_device_type():
    ua = request.headers.get('User-Agent', '').lower()
    accept = request.headers.get('Accept', '').lower()
    
    # PRIORITY 1: Smart TV - dispositivo principal del proyecto
    # Philco y otras smart TVs conocidas
    tv_keywords = ['smarttv', 'smart-tv', 'philco', 'googletv', 'appletv', 'roku', 'chromecast', 'tizen', 'webos', 'netcast', 'hbbtv', 'aftb', 'linux', 'arm']
    if any(keyword in ua for keyword in tv_keywords):
        # Si no es un teléfono o tablet, es TV
        if 'android' not in ua and 'iphone' not in ua and 'ipad' not in ua and 'mobile' not in ua:
            return 'tv'
    
    # PRIORITY 2: PC - Desktop sin móvil
    if any(x in ua for x in ['windows nt', 'macintosh', 'linux']):
        if 'mobile' not in ua and 'android' not in ua and 'tablet' not in ua:
            return 'pc'
    
    # PRIORITY 3: Móvil
    mobile_keywords = ['android', 'iphone', 'ipad', 'ipod', 'mobile', 'tablet', 'opera mini', 'opera mobi', 'blackberry', 'windows phone']
    if any(keyword in ua for keyword in mobile_keywords):
        return 'mobile'
    
    # Default: TV (proyecto orientado a TV)
    return 'tv'

@app.route('/')
def index():
    device = get_device_type()
    
    if device == 'tv':
        return send_file('tv.html')
    elif device == 'mobile':
        return send_file('mobile.html')
    else:
        return send_file('pc.html')

@app.route('/tv')
def tv():
    return send_file('tv.html')

@app.route('/mobile')
def mobile():
    return send_file('mobile.html')

@app.route('/pc')
def pc():
    return send_file('pc.html')

@app.route('/api/search')
def api_search():
    q = request.args.get('q', '').strip().lower()
    offset = int(request.args.get('offset', 0))
    limit = int(request.args.get('limit', 20))
    
    if not q:
        return jsonify({'streams': []})

    if offset == 0:
        cache_key = "search:" + q
        cached = get_cached(cache_key)
        if cached:
            cached['cached'] = True
            cached['status'] = 'cached'
            return jsonify(cached)

    result = search(q, limit=limit, offset=offset)

    if result.get('streams'):
        if offset == 0:
            try:
                set_cached("search:" + q, result)
            except:
                pass
        return jsonify(result)

    if offset == 0:
        fallback = get_fallback("search:" + q)
        if fallback:
            fallback['status'] = 'degraded'
            fallback['source'] = 'fallback'
            return jsonify(fallback)

    return jsonify({'streams': [], 'status': 'error', 'error': result.get('error', 'no data')})

@app.route('/api/status')
def api_status():
    from scraper.searchtv import get_status
    return jsonify(get_status())

@app.route('/api/debug')
def api_debug():
    ua = request.headers.get('User-Agent', '')
    device = get_device_type()
    return jsonify({
        'user_agent': ua,
        'detected_device': device
    })

@app.route('/api/channel/<channel>')
def api_channel(channel):
    result = get_best_stream(channel)
    if result:
        return jsonify({'status': 'ok', 'stream': result})
    return jsonify({'status': 'error', 'error': 'channel not found'})

@app.route('/api/channels')
def api_channels():
    channels = get_all_channels()
    return jsonify({'channels': channels, 'total': len(channels)})

@app.route('/api/stats')
def api_stats():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status, COUNT(*) as count FROM streams GROUP BY status")
    stats = {row['status']: row['count'] for row in cursor.fetchall()}
    cursor.execute("SELECT COUNT(*) as total FROM streams")
    stats['total'] = cursor.fetchone()['total']
    return jsonify(stats)

@app.route('/api/ingest')
def api_ingest():
    from ingest import ingest_playlist
    try:
        ingest_playlist()
        return jsonify({'status': 'ok', 'message': 'data ingested'})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)})

@app.route('/api/ingest/nodes')
def api_ingest_nodes():
    from ingest_nodes import ingest_nodes
    try:
        ingest_nodes()
        return jsonify({'status': 'ok', 'message': 'nodes ingested'})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)})

@app.route('/api/discover')
def api_discover():
    from discover import discover
    try:
        discover()
        return jsonify({'status': 'ok', 'message': 'discovery complete'})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)})

@app.route('/api/unified_ingest')
def api_unified_ingest():
    from unified_ingest import load_all_raw
    try:
        streams, nodes = load_all_raw()
        return jsonify({'status': 'ok', 'streams': streams, 'nodes': nodes})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)})

@app.route('/api/validate')
def api_validate():
    from validate import validate_batch
    try:
        count = validate_batch(200, 30)
        return jsonify({'status': 'ok', 'validated': count})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)})

@app.route('/api/validate/all')
def api_validate_all():
    from validate import validate_all
    try:
        validate_all(500, 50)
        return jsonify({'status': 'ok', 'message': 'validation complete'})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, threaded=True, debug=False)