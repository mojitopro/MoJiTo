#!/usr/bin/env python3
import os
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

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
        return send_file('mobile.html')
    return send_file('tv.html')

@app.route('/tv')
def tv():
    return send_file('tv.html')

@app.route('/api/channels')
def api_channels():
    from selector import get_all_channels
    return jsonify(get_all_channels())

@app.route('/api/stream/<path:channel>')
def api_stream(channel):
    from selector import get_best_stream
    result = get_best_stream(channel)
    if result:
        return jsonify({
            'status': 'ok',
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
        return jsonify([])
    return jsonify(search_channels(q))

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
