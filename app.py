#!/usr/bin/env python3
import os
import time
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

from scraper.searchtv import search, get_status
from core.cache import get_cached, set_cached, get_fallback

LOG_ENABLED = True

def log(msg):
    if LOG_ENABLED:
        print(f"[{time.strftime('%H:%M:%S')}] {msg}")

@app.route('/')
def index():
    return send_file('tv.html')

@app.route('/api/search')
def api_search():
    q = request.args.get('q', '').strip().lower()
    if not q:
        return jsonify({'streams': []})
    
    cache_key = f"search:{q}"
    
    log(f"Search: {q}")
    
    cached_data = get_cached(cache_key)
    if cached_data:
        log(f"Cache hit: {len(cached_data['streams'])} streams")
        cached_data['cached'] = True
        cached_data['status'] = 'cached'
        return jsonify(cached_data)
    
    log("Scraping live...")
    result = search(q)
    log(f"Live result: {result.get('results', 0)} streams, status: {result.get('status')}")
    
    if result.get('streams'):
        set_cached(cache_key, result)
        return jsonify(result)
    
    log("No streams, trying fallback...")
    fallback_data = get_fallback(cache_key)
    if fallback_data:
        log(f"Fallback: {len(fallback_data.get('streams', []))} streams")
        fallback_data['status'] = 'degraded'
        fallback_data['source'] = 'fallback'
        return jsonify(fallback_data)
    
    return jsonify({
        'streams': [],
        'status': 'error',
        'error': result.get('error', 'no data')
    })

@app.route('/api/status')
def api_status():
    return jsonify(get_status())

if __name__ == '__main__':
    print('MoJiTo TV - Resilient')
    app.run(host='0.0.0.0', port=8080, threaded=True, debug=False)