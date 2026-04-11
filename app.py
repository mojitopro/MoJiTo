#!/usr/bin/env python3
from flask import Flask, request, jsonify, send_file
import os

app = Flask(__name__)

CHANNELS = {
    'espn': [
        {'title': 'ESPN HD', 'url': 'https://stream1.animeindo.my.id/live/espn/playlist.m3u8'},
        {'title': 'ESPN SD', 'url': 'https://stream2.example.com/espn-sd.m3u8'},
    ],
    'fox': [
        {'title': 'FOX HD', 'url': 'https://stream1.animeindo.my.id/live/fox/playlist.m3u8'},
    ],
    'beinsports': [
        {'title': 'beIN Sports HD', 'url': 'https://stream1.animeindo.my.id/live/bein/playlist.m3u8'},
    ],
    'directv': [
        {'title': 'Directv HD', 'url': 'https://stream1.animeindo.my.id/live/direc/playlist.m3u8'},
    ],
    'espn2': [
        {'title': 'ESPN 2 HD', 'url': 'https://stream1.animeindo.my.id/live/espn2/playlist.m3u8'},
    ],
    'nba': [
        {'title': 'NBA HD', 'url': 'https://stream1.animeindo.my.id/live/nba/playlist.m3u8'},
    ],
    'mlb': [
        {'title': 'MLB HD', 'url': 'https://stream1.animeindo.my.id/live/mlb/playlist.m3u8'},
    ],
    'nfl': [
        {'title': 'NFL HD', 'url': 'https://stream1.animeindo.my.id/live/nfl/playlist.m3u8'},
    ],
}

@app.route('/')
def index():
    return send_file('tv.html')

@app.route('/api/search')
def api_search():
    q = request.args.get('q', '').strip().lower()
    if not q:
        return jsonify({'streams': []})
    
    results = []
    for name, streams in CHANNELS.items():
        if q in name:
            results.extend(streams)
    
    if not results:
        return jsonify({'streams': [{'title': f'{q.upper()} Stream', 'url': 'https://stream1.animeindo.my.id/live/'+q+'/playlist.m3u8'}]})
    
    return jsonify({'streams': results, 'hasMore': False})

if __name__ == '__main__':
    print('MoJiTo TV - Hardcoded Channels')
    app.run(host='0.0.0.0', port=8080, threaded=True)