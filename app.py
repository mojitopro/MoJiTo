#!/usr/bin/env python3
import os, json, subprocess, urllib.request, urllib.parse
from datetime import datetime
from pathlib import Path
from typing import List, Dict

import os
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

CFG = {"name":"SōF — Shadow of Fire","group":"SōF — Shadow of Fire",
       "test":8,"file":"sof-playlist.json"}

ST = "https://searchtv.net/"
scraper = None

try:
    import cloudscraper
    scraper = cloudscraper.create_scraper()
    scraper.get(ST)
except: pass

def log(m, l="INFO"):
    print(f"{l}: {m}")

@app.route('/')
def index():
    return send_file(os.path.join(os.path.dirname(__file__), 'tv.html'))

@app.route('/api/search')
def api_search():
    q = request.args.get('q', '').strip().lower()
    if not q:
        return jsonify({'streams': []})
    
    if not scraper:
        return jsonify({'streams': [], 'error': 'cloudscraper no disponible'})
    
    try:
        resp = scraper.get(f"{ST}search/?query={urllib.parse.quote(q)}", timeout=10)
        if resp.status_code != 200:
            return jsonify({'streams': [], 'error': f'HTTP {resp.status_code}'})
        
        items = resp.json()
        streams = []
        
        for item_id, info in items.items():
            try:
                r = scraper.get(f"{ST}stream/uuid/{item_id}/", timeout=3)
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
        
        return jsonify({'streams': streams, 'hasMore': False})
        
    except Exception as e:
        return jsonify({'streams': [], 'error': str(e)[:100]})

if __name__ == '__main__':
    print('MoJiTo TV')
    app.run(host='0.0.0.0', port=8080, threaded=True, debug=False)