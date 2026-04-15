#!/usr/bin/env python3
import time
import os
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

def get_device_type():
    ua = request.headers.get('User-Agent', '').lower()
    
    tv_keywords = ['smarttv', 'smart-tv', 'philco', 'googletv', 'appletv', 'roku', 'chromecast', 'tizen', 'webos', 'netcast', 'hbbtv', 'aftb', 'linux', 'arm']
    if any(keyword in ua for keyword in tv_keywords):
        if 'android' not in ua and 'iphone' not in ua and 'ipad' not in ua and 'mobile' not in ua:
            return 'tv'
    
    if any(x in ua for x in ['windows nt', 'macintosh', 'linux']):
        if 'mobile' not in ua and 'android' not in ua and 'tablet' not in ua:
            return 'pc'
    
    mobile_keywords = ['android', 'iphone', 'ipad', 'ipod', 'mobile', 'tablet', 'opera mini', 'opera mobi', 'blackberry', 'windows phone']
    if any(keyword in mobile_keywords for keyword in ua.split()):
        return 'mobile'
    
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

@app.route('/api/channels')
def api_channels():
    from selector import get_all_channels
    channels = get_all_channels()
    return jsonify(channels)

@app.route('/api/channel/<path:channel>')
def api_channel(channel):
    from selector import get_best_stream
    result = get_best_stream(channel)
    if result:
        return jsonify({
            'status': 'ok',
            'url': result.get('url'),
            'channel': result.get('channel'),
            'fallbacks': result.get('fallbacks', []),
            'latency': result.get('latency')
        })
    return jsonify({'status': 'error', 'error': 'no stream available'})

@app.route('/api/stream/<path:channel>')
def api_stream(channel):
    from selector import get_best_stream, get_channel_streams
    all_streams = get_channel_streams(channel)
    
    if not all_streams:
        return jsonify({'status': 'error', 'error': 'channel not found'})
    
    # Fast: use score-based selection (no validation)
    best = get_best_stream(channel, max_retries=1, validate=False)
    
    if best:
        fallbacks = [s['url'] for s in all_streams if s['url'] != best['url']][:5]
        return jsonify({
            'status': 'ok',
            'url': best['url'],
            'channel': best['channel'],
            'fallbacks': fallbacks,
            'total_streams': len(all_streams)
        })
    
    return jsonify({
        'status': 'ok',
        'url': all_streams[0]['url'],
        'fallbacks': [s['url'] for s in all_streams[1:5]],
        'channel': channel
    })

@app.route('/api/search')
def api_search():
    from selector import search_channels
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])
    results = search_channels(q)
    return jsonify(results)

@app.route('/api/category/<path:category>')
def api_category(category):
    from selector import get_category_channels
    results = get_category_channels(category)
    return jsonify(results)

@app.route('/api/stats')
def api_stats():
    from selector import get_stats
    return jsonify(get_stats())

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
