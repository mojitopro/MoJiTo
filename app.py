#!/usr/bin/env python3
import time
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

from scraper.searchtv import search
from core.cache import get_cached, set_cached, get_fallback

def get_device_type():
    ua = request.headers.get('User-Agent', '').lower()
    accept = request.headers.get('Accept', '').lower()
    
    # PRIORITY 1: Mobile - keywords más comunes de móviles
    mobile_keywords = ['android', 'iphone', 'ipad', 'ipod', 'mobile', 'tablet', 'opera mini', 'opera mobi', 'blackberry', 'windows phone', 'safari']
    if any(keyword in ua for keyword in mobile_keywords):
        # Si es mobile Y NO es desktop/safari de escritorio
        if 'windows nt' not in ua and 'mac os x' not in ua:
            return 'mobile'
        # iPhone/iPad con Safari
        if 'iphone' in ua or 'ipad' in ua or 'ipod' in ua:
            return 'mobile'
    
    # PRIORITY 2: PC - Desktop OS sin móvil
    pc_keywords = ['windows nt', 'macintosh', 'linux', 'firefox', 'chrome']
    if any(keyword in ua for keyword in pc_keywords):
        if 'mobile' not in ua and 'android' not in ua and 'tablet' not in ua:
            return 'pc'
    
    # PRIORITY 3: Smart TV
    tv_keywords = ['smarttv', 'smart-tv', 'philco', 'googletv', 'appletv', 'roku', 'chromecast', 'tizen', 'webos', 'netcast', 'hbbtv', 'aftb']
    if any(keyword in ua for keyword in tv_keywords):
        return 'tv'
    
    # Default: mobile (más común)
    return 'mobile'

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, threaded=True, debug=False)