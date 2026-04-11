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
    page = int(request.args.get('page', 1))
    
    if not q:
        return jsonify({'streams': []})
    
    limit = 20
    start_idx = (page - 1) * limit
    
    try:
        import urllib.request
        import urllib.parse
        import json
        import re
        
        req = urllib.request.Request(
            f'https://searchtv.net/search/?query={urllib.parse.quote(q)}',
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://searchtv.net/'
            }
        )
        
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read().decode()
            items = list(json.loads(data).keys())
        
        streams = []
        downloaded = 0
        i = start_idx
        
        while downloaded < limit and i < len(items):
            try:
                stream_req = urllib.request.Request(
                    f'https://searchtv.net/stream/uuid/{items[i]}/',
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                )
                with urllib.request.urlopen(stream_req, timeout=3) as sr:
                    text = sr.read().decode()
                    if '#EXTM3U' in text:
                        title = str(items[i])
                        url = ''
                        for line in text.split('\n'):
                            if line.startswith('#EXTINF:'):
                                parts = line.split(',')
                                if len(parts) > 1:
                                    raw = parts[1].strip().split('==>')[0].strip()
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
        return jsonify({'streams': [], 'error': str(e)[:100]})

if __name__ == '__main__':
    print('MoJiTo TV')
    app.run(host='0.0.0.0', port=8080, threaded=True, debug=False)