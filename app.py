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
        import requests
        import urllib.parse
        import json
        import re
        
        s = requests.Session()
        s.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://searchtv.net/'
        })
        
        proxies_list = [
            {'http': 'http://167.71.192.89:1080', 'https': 'http://167.71.192.89:1080'},
            {'http': 'http://207.180.243.216:5690', 'https': 'http://207.180.243.216:5690'},
            {'http': 'http://195.201.92.52:3128', 'https': 'http://195.201.92.52:3128'},
            {'http': 'http://89.187.175.101:3128', 'https': 'http://89.187.175.101:3128'},
            {'http': 'http://154.38.163.109:3128', 'https': 'http://154.38.163.109:3128'},
            {'http': 'http://167.71.75.51:3128', 'https': 'http://167.71.75.51:3128'},
            None
        ]
        
        items = None
        for proxy in proxies_list:
            try:
                r = s.get(
                    'https://searchtv.net/search/?query=' + urllib.parse.quote(q),
                    proxies=proxy,
                    timeout=8
                )
                if r.status_code == 200 and '<' not in r.text[:10]:
                    items = list(r.json().keys())
                    break
            except:
                continue
        
        if not items:
            return jsonify({'streams': [], 'error': 'all_proxies_failed'})
        
        streams = []
        downloaded = 0
        i = start_idx
        
        while downloaded < limit and i < len(items):
            try:
                sr = s.get(f'https://searchtv.net/stream/uuid/{items[i]}/', timeout=3)
                if '#EXTM3U' in sr.text:
                    title = str(items[i])
                    url = ''
                    for line in sr.text.split('\n'):
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
        return jsonify({'streams': [], 'error': str(e)[:150]})

if __name__ == '__main__':
    print('MoJiTo TV')
    app.run(host='0.0.0.0', port=8080, threaded=True, debug=False)