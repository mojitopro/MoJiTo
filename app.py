#!/usr/bin/env python3
import time
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

from scraper.searchtv import search
from core.cache import get_cached, set_cached, get_fallback

@app.route('/')
def index():
    return send_file('tv.html')

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