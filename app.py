#!/usr/bin/env python3
from flask import Flask, request, jsonify, send_file
import os
import threading

app = Flask(__name__)

@app.route('/')
def index():
    return send_file(os.path.join(os.path.dirname(__file__), 'tv.html'))

@app.route('/api/search')
def api_search():
    q = request.args.get('q', '').strip().lower()
    page = int(request.args.get('page', 1))
    
    if not q:
        return jsonify({'streams': []})
    
    limit = 20
    start_idx = (page - 1) * limit
    
    try:
        import cloudscraper
        import urllib.parse
        scraper = cloudscraper.create_scraper()
        
        resp = scraper.get(f'https://searchtv.net/search/?query={urllib.parse.quote(q)}', timeout=10)
        
        if resp.status_code != 200:
            return jsonify({'streams': []})
        
        items = list(resp.json().keys())
        
        streams = []
        downloaded = 0
        i = start_idx
        
        while downloaded < limit and i < len(items):
            try:
                stream_resp = scraper.get(f'https://searchtv.net/stream/uuid/{items[i]}/', timeout=2)
                if 'EXTM3U' in stream_resp.text:
                    title = str(items[i])
                    url = ''
                    for line in stream_resp.text.split('\n'):
                        if line.startswith('#EXTINF:'):
                            parts = line.split(',')
                            if len(parts) > 1:
                                raw = parts[1].strip().split('==>')[0].strip()
                                import re
                                title = re.sub(r'\s*\(\d+\)\s*$', '', raw).strip()
                        elif line.startswith('http'):
                            url = line.strip()
                            break
                    if url:
                        streams.append({'title': title, 'url': url})
                        downloaded += 1
            except:
                pass
            i += 1
        
        streams.sort(key=lambda x: 1 if '1080' in x['title'].lower() or 'hd' in x['title'].lower() else 2)
        
        has_more = i < len(items)
        
        return jsonify({'streams': streams, 'hasMore': has_more})
        
    except Exception as e:
        return jsonify({'streams': [], 'error': str(e)[:50]})

if __name__ == '__main__':
    print('SŌF TV - Fast HD Priority')
    app.run(host='0.0.0.0', port=8080, threaded=True, debug=False)