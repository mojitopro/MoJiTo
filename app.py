#!/usr/bin/env python3
"""
MoJiTo Dashboard Server
"""
from flask import Flask, jsonify, request, send_file
from pathlib import Path
import sqlite3

app = Flask(__name__)

ROOT = Path(__file__).parent
DB_PATH = str(ROOT / 'data' / 'normalized' / 'streams.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_stats():
    db = get_db()
    c = db.cursor()
    
    stats = {}
    
    c.execute("SELECT COUNT(*) FROM streams")
    stats['streams'] = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM clusters")
    stats['clusters'] = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM cluster_streams")
    stats['clustered'] = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM fusion_state WHERE active_stream IS NOT NULL")
    stats['fusion_active'] = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM stream_metrics")
    stats['metrics'] = c.fetchone()[0]
    
    return stats


def get_top_clusters(limit=20):
    db = get_db()
    c = db.cursor()
    
    c.execute(f"""
        SELECT c.canonical_name, c.confidence,
               (SELECT COUNT(*) FROM cluster_streams WHERE cluster_id = c.cluster_id) as stream_count
        FROM clusters c
        ORDER BY stream_count DESC
        LIMIT {limit}
    """)
    
    clusters = []
    for row in c.fetchall():
        clusters.append({
            'name': row[0],
            'confidence': row[1],
            'streams': row[2]
        })
    
    return clusters


@app.route('/')
def index():
    return send_file('tv-lite.html')


@app.route('/tv-old')
@app.route('/tv-old.html')
def tv_old():
    return send_file('tv.html')


@app.route('/dashboard')
@app.route('/dashboard.html')
def dashboard():
    stats = get_stats()
    clusters = get_top_clusters(20)
    
    fusion_pct = 0
    if stats['clusters'] > 0:
        fusion_pct = min(100, (stats['fusion_active'] / stats['clusters']) * 100)
    
    # Generate cluster cards HTML
    clusters_html = ''
    for i, cl in enumerate(clusters):
        active = 'cold' if i >= stats['fusion_active'] else 'active'
        clusters_html += f'''
        <div class="cluster-card">
            <div class="name">{cl['name'][:50]}</div>
            <div class="streams"><span>{cl['streams']}</span> streams · {cl['confidence']:.0%} confidence</div>
            <span class="status {active}">{active}</span>
        </div>
        '''
    
    if not clusters_html:
        clusters_html = '<p style="color:#666;">No hay clusters aún. Ejecuta ./run.sh pipeline</p>'
    
    # Read template
    with open('dashboard.html') as f:
        html = f.read()
    
    # Replace placeholders
    html = html.replace('{{STREAMS}}', str(stats['streams']))
    html = html.replace('{{CLUSTERS}}', str(stats['clusters']))
    html = html.replace('{{CLUSTERED}}', str(stats['clustered']))
    html = html.replace('{{FUSION_ACTIVE}}', str(stats['fusion_active']))
    html = html.replace('{{FUSION_PCT}}', str(int(fusion_pct)))
    html = html.replace('{{CLUSTERS_HTML}}', clusters_html)
    
    return html


@app.route('/api/stats')
def api_stats():
    stats = get_stats()
    return jsonify({
        'status': 'ok',
        'stats': stats
    })


@app.route('/api/channels')
def api_channels():
    limit = request.args.get('limit', 50, type=int)
    clusters = get_top_clusters(limit)
    return jsonify({
        'status': 'ok',
        'channels': clusters
    })


@app.route('/api/cluster/<cluster_id>')
def api_cluster(cluster_id):
    db = get_db()
    c = db.cursor()
    
    c.execute("SELECT * FROM clusters WHERE cluster_id = ?", (cluster_id,))
    cluster = dict(c.fetchone()) if c.fetchone() else None
    
    if not cluster:
        return jsonify({'status': 'error', 'error': 'cluster not found'})
    
    c.execute("""
        SELECT stream_url, priority, is_primary 
        FROM cluster_streams 
        WHERE cluster_id = ?
        ORDER BY priority DESC
    """, (cluster_id,))
    
    streams = [dict(row) for row in c.fetchall()]
    
    return jsonify({
        'status': 'ok',
        'cluster': cluster,
        'streams': streams
    })


@app.route('/tv')
@app.route('/tv.html')
def tv():
    return send_file('tv.html')


@app.route('/api/tv')
def api_tv():
    import json
    import re
    
    ROOT = Path(__file__).parent
    
    all_channels = []
    seen = set()
    
    known_channels = [
        {'name': 'ESPN', 'url': 'http://38.41.8.1:8000/play/a0t3'},
        {'name': 'ESPN 2', 'url': 'http://38.41.8.1:8000/play/a0rp'},
        {'name': 'ESPN 3', 'url': 'http://38.41.8.1:8000/play/a0sw'},
        {'name': 'ESPN 4', 'url': 'http://38.41.8.1:8000/play/a0sv'},
        {'name': 'ESPN 5', 'url': 'http://38.41.8.1:8000/play/a0rm'},
        {'name': 'ESPN 6', 'url': 'http://38.41.8.1:8000/play/a0sx'},
        {'name': 'ESPN 7', 'url': 'http://38.41.8.1:8000/play/a0zx'},
        {'name': 'Fox Sports 1', 'url': 'http://38.41.8.1:8000/play/a0sw'},
        {'name': 'Fox Sports 2', 'url': 'http://38.41.8.1:8000/play/a0sv'},
        {'name': 'Fox Sports 3', 'url': 'http://38.41.8.1:8000/play/a0rm'},
        {'name': 'TNT Sports', 'url': 'http://38.41.8.1:8000/play/a0sx'},
        {'name': 'TyC Sports', 'url': 'http://38.41.8.1:8000/play/a0zx'},
        {'name': 'Win Sports', 'url': 'http://38.41.8.1:8000/play/a0t3'},
        {'name': 'HBO', 'url': 'http://38.187.3.110:8000/play/a07z/index.m3u8'},
        {'name': 'HBO 2', 'url': 'http://45.181.120.65:9087/play/130/index.m3u8'},
        {'name': 'HBO Family', 'url': 'http://45.181.120.65:9087/play/a0gt/index.m3u8'},
        {'name': 'HBO Plus', 'url': 'http://38.250.125.162:9800/play/093/index.m3u8'},
        {'name': 'Star Channel', 'url': 'http://45.181.120.65:9087/play/109/index.m3u8'},
        {'name': 'Cinemax', 'url': 'http://38.41.8.1:8000/play/a0rp'},
        {'name': 'AMC', 'url': 'http://38.41.8.1:8000/play/a0t3'},
        {'name': 'TNT', 'url': 'http://38.41.8.1:8000/play/a0sv'},
        {'name': 'FX', 'url': 'http://38.41.8.1:8000/play/a0sw'},
        {'name': 'AXN', 'url': 'http://38.41.8.1:8000/play/a0rp'},
        {'name': 'Sony', 'url': 'http://38.41.8.1:8000/play/a0t7'},
        {'name': 'Universal', 'url': 'http://38.41.8.1:8000/play/a0t3'},
        {'name': 'Paramount', 'url': 'http://38.41.8.1:8000/play/a0sx'},
        {'name': 'Discovery Channel', 'url': 'http://38.41.8.1:8000/play/a0rm'},
        {'name': 'Nat Geo', 'url': 'http://38.41.8.1:8000/play/a0t3'},
        {'name': 'History', 'url': 'http://38.41.8.1:8000/play/a0t7'},
        {'name': 'Animal Planet', 'url': 'http://38.41.8.1:8000/play/a0rp'},
        {'name': 'Disney Channel', 'url': 'http://38.41.8.1:8000/play/a0sv'},
        {'name': 'Nickelodeon', 'url': 'http://38.41.8.1:8000/play/a0rm'},
        {'name': 'Cartoon Network', 'url': 'http://181.119.86.1:8000/play/a01g'},
        {'name': 'MTV', 'url': 'http://38.41.8.1:8000/play/a0sx'},
        {'name': 'CNN', 'url': 'http://38.41.8.1:8000/play/a0t3'},
        {'name': 'BBC World', 'url': 'http://38.41.8.1:8000/play/a0sw'},
        {'name': 'DW', 'url': 'http://38.41.8.1:8000/play/a0sv'},
    ]
    
    for ch in known_channels:
        url = ch['url']
        key = (ch['name'], url)
        if key not in seen:
            seen.add(key)
            all_channels.append({
                'name': ch['name'],
                'url': url,
                'streams': 3,
                'fusion': True,
                'backups': [url]
            })
    
    for fname in ['working_streams.json', 'premium_working.json']:
        try:
            with open(ROOT / fname) as f:
                data = json.load(f)
            ch_list = data.get('channels', data) if isinstance(data, dict) else data
            for ch in ch_list:
                name = ch.get('name', '')
                url = ch.get('url', '')
                fallbacks = ch.get('fallbacks', [])
                if name and url and (name, url) not in seen:
                    seen.add((name, url))
                    all_channels.append({
                        'name': name,
                        'url': url,
                        'streams': len(fallbacks) + 1,
                        'fusion': len(fallbacks) > 0,
                        'backups': [url] + fallbacks
                    })
        except:
            pass
    
    return jsonify({
        'status': 'ok',
        'channels': all_channels,
        'total': len(all_channels)
    })


@app.route('/api/play/<cluster_id>')
def api_play(cluster_id):
    db = get_db()
    c = db.cursor()
    
    # Get active stream from fusion_state
    c.execute("""
        SELECT active_stream, backup_streams, switch_count
        FROM fusion_state 
        WHERE cluster_id = ?
    """, (cluster_id,))
    
    row = c.fetchone()
    
    if row and row[0]:
        url = row[0]
        return jsonify({
            'status': 'ok',
            'url': url,
            'backups': row[1],
            'switches': row[2]
        })
    
    # Fallback: get first stream from cluster
    c.execute("""
        SELECT stream_url 
        FROM cluster_streams 
        WHERE cluster_id = ?
        ORDER BY priority DESC
        LIMIT 1
    """, (cluster_id,))
    
    row = c.fetchone()
    
    if row:
        return jsonify({
            'status': 'ok',
            'url': row[0]
        })
    
    return jsonify({
        'status': 'error',
        'error': 'no stream available'
    })


@app.route('/hls.min.js')
def hls_js():
    import requests
    try:
        r = requests.get('https://cdn.jsdelivr.net/npm/hls.js@0.14.0/dist/hls.min.js', timeout=10)
        return r.text, 200, {'Content-Type': 'application/javascript'}
    except:
        return '', 404


@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'mojito-dashboard'})


if __name__ == '__main__':
    import os
    import argparse
    
    parser = argparse.ArgumentParser(description='MoJiTo Dashboard')
    parser.add_argument('--port', '-p', type=int, default=int(os.environ.get('PORT', 8080)))
    parser.add_argument('--host', default='0.0.0.0')
    args = parser.parse_args()
    
    print(f"🌐 MoJiTo Dashboard: http://{args.host}:{args.port}")
    print(f"   Dashboard: http://{args.host}:{args.port}/")
    print(f"   API:      http://{args.host}:{args.port}/api/stats")
    print(f"   Channels: http://{args.host}:{args.port}/api/channels")
    
    app.run(host=args.host, port=args.port, threaded=True, debug=False)