#!/usr/bin/env python3
import os
from pathlib import Path
from flask import Flask, request, jsonify, redirect, send_file

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent

def wants_premium_only():
    category = request.args.get('category', '').strip().lower()
    premium_flag = request.args.get('premium', '').strip().lower()
    mode = request.args.get('mode', '').strip().lower()

    if category in {'premium', 'on-demand', 'ondemand', 'vod'}:
        return True
    if premium_flag in {'1', 'true', 'yes', 'on'}:
        return True
    if mode in {'premium', 'on-demand', 'ondemand'}:
        return True
    return False

@app.route('/')
def index():
    return send_file(str(BASE_DIR / 'tv.html'))

@app.route('/tv.html')
@app.route('/tv')
def tv():
    return send_file(str(BASE_DIR / 'tv.html'))

@app.route('/api/channels')
def api_channels():
    from selector import get_all_channels
    premium_only = wants_premium_only()
    sort_by = request.args.get('sort', 'latency').strip().lower()
    limit = request.args.get('limit', type=int)
    channels = get_all_channels(limit=limit, premium_only=premium_only, sort_by=sort_by)

    return jsonify({
        'status': 'ok',
        'category': 'premium' if premium_only else 'all',
        'sort': sort_by,
        'channels': channels,
    })

@app.route('/api/stream/<path:channel>')
@app.route('/api/channel/<path:channel>')
def api_stream(channel):
    from selector import get_best_stream
    result = get_best_stream(channel, premium_only=wants_premium_only())
    if result:
        return jsonify({
            'status': 'ok',
            'stream': result,
            **result
        })
    return jsonify({
        'status': 'error',
        'error': 'channel not found',
        'url': None,
        'fallbacks': []
    })

@app.route('/api/search')
def api_search():
    from selector import search_channels
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({
            'status': 'ok',
            'streams': [],
        })
    premium_only = wants_premium_only()
    results = search_channels(q, premium_only=premium_only)
    return jsonify({
        'status': 'ok',
        'premium_only': premium_only,
        'streams': results,
    })

@app.route('/api/stats')
def api_stats():
    from selector import get_stats
    return jsonify(get_stats())

@app.route('/api/premium')
def api_premium():
    import json
    from pathlib import Path
    path = BASE_DIR / 'premium_consolidated.json'
    if path.exists():
        with open(path) as f:
            data = json.load(f)
            return jsonify({'status': 'ok', 'channels': data.get('channels', [])})
    return jsonify({'status': 'error', 'channels': []})

@app.route('/api/debug')
def api_debug():
    ua = request.headers.get('User-Agent', '')
    return jsonify({
        'user_agent': ua,
        'html_version': 'modern'
    })

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'mojito-tv'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, threaded=True, debug=False)