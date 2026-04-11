#!/usr/bin/env python3
from flask import Flask, request, jsonify, send_file
import os

app = Flask(__name__)

@app.route('/')
def index():
    return send_file(os.path.join(os.path.dirname(__file__), 'tv.html'))

@app.route('/api/search')
def api_search():
    q = request.args.get('q', '').strip().lower()
    if not q:
        return jsonify({'streams': []})
    
    try:
        import cloudscraper
        import urllib.parse
        import re
        
        scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False},
            interpreter='native'
        )
        
        r1 = scraper.get('https://searchtv.net/', timeout=15)
        
        resp = scraper.get(f'https://searchtv.net/search/?query={urllib.parse.quote(q)}', timeout=15)
        
        if resp.status_code != 200:
            return jsonify({'streams': [], 'debug': {'status': resp.status_code, 'text': resp.text[:100]}})
        
        text = resp.text
        if text.startswith('<'):
            return jsonify({'streams': [], 'debug': 'html_response', 'text': text[:200]})
        
        items = resp.json()
        
        streams = []
        for item_id, info in items.items():
            try:
                r = scraper.get(f'https://searchtv.net/stream/uuid/{item_id}/', timeout=3)
                if 'EXTM3U' in r.text:
                    for line in r.text.strip().split('\n'):
                        if line.startswith('http'):
                            streams.append({
                                'url': line.strip(),
                                'title': info.get('title', item_id)
                            })
                            break
            except:
                pass
        
        streams.sort(key=lambda x: 1 if '1080' in x['title'].lower() or 'hd' in x['title'].lower() else 2)
        
        return jsonify({'streams': streams, 'hasMore': False, 'count': len(streams)})
        
    except Exception as e:
        import traceback
        return jsonify({'streams': [], 'error': str(e)[:100], 'trace': traceback.format_exc()[:200]})

if __name__ == '__main__':
    print('MoJiTo TV')
    app.run(host='0.0.0.0', port=8080, threaded=True, debug=False)