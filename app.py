#!/usr/bin/env python3
import time
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

from scraper.searchtv import search
from core.cache import get_cached, set_cached, get_fallback

def get_device_type():
    ua = request.headers.get('User-Agent', '').lower()
    accept = request.headers.get('Accept', '').lower()
    
    # Check for Smart TV indicators in User-Agent
    tv_indicators = ['smarttv', 'smart-tv', 'philco', 'googletv', 'appletv', 'roku', 'chromecast', 'tizen', 'webos', 'netcast', 'linux', 'arm']
    is_tv_ua = any(indicator in ua for indicator in tv_indicators)
    
    # PC: typical desktop OS without mobile indicators
    is_pc = any(x in ua for x in ['windows', 'macintosh']) and 'mobile' not in ua
    
    # Mobile: typical mobile indicators
    is_mobile = any(x in ua for x in ['android', 'iphone', 'mobile', 'tablet'])
    
    # Additional check: if no user-agent but accepts HTML, default to TV
    if not ua or ua == '*':
        return 'tv'
    
    # If appears to be mobile device
    if is_mobile:
        return 'mobile'
    
    # If has PC indicators and no mobile
    if is_pc:
        return 'pc'
    
    # Default to TV for smart TV browsers / WebViews
    if is_tv_ua or 'linux' in ua or 'arm' in ua:
        return 'tv'
    
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, threaded=True, debug=False)