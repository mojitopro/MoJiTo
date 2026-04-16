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

def get_device_type():
    ua = request.headers.get('User-Agent', '').lower()
    tv_keywords = ['smarttv', 'smart-tv', 'philco', 'googletv', 'appletv', 'roku', 'chromecast', 'tizen', 'webos', 'netcast', 'hbbtv', 'linux', 'arm']
    if any(keyword in ua for keyword in tv_keywords):
        if 'android' not in ua and 'iphone' not in ua and 'ipad' not in ua and 'mobile' not in ua:
            return 'tv'
    if any(x in ua for x in ['android', 'iphone', 'ipad', 'ipod', 'mobile', 'tablet']):
        return 'mobile'
    return 'tv'

@app.route('/')
def index():
    device = get_device_type()
    if device == 'mobile':
        return send_file(str(BASE_DIR / 'mobile.html'))
    return send_file(str(BASE_DIR / 'tv.html'))

@app.route('/tv.html')
@app.route('/tv')
def tv():
    return send_file(str(BASE_DIR / 'tv.html'))

@app.route('/tv-addictive.html')
@app.route('/tv-addictive')
def tv_addictive():
    return redirect('/tv', code=302)

@app.route('/api/channels')
def api_channels():
    from selector import get_all_channels
    premium_only = wants_premium_only()
    sort_by = request.args.get('sort', 'name').strip().lower()
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

@app.route('/api/debug')
def api_debug():
    return jsonify({
        'user_agent': request.headers.get('User-Agent', ''),
        'detected_device': get_device_type()
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, threaded=True, debug=False)
