#!/usr/bin/env python3
"""
MoJiTo Dashboard Server
"""
from flask import Flask, jsonify, request, send_file, Response, stream_with_context
from pathlib import Path
import sqlite3
import requests

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
    
    ROOT = Path(__file__).parent
    groups = {}
    
    for fname in ['custom_channels.json', 'premium_working.json', 'working_streams.json']:
        try:
            with open(ROOT / fname) as f:
                data = json.load(f)
            ch_list = data.get('channels', data) if isinstance(data, dict) else data
            for ch in ch_list:
                name = ch.get('name', '').strip()
                url = ch.get('url', '').strip()
                if name and url:
                    if name not in groups:
                        groups[name] = []
                    groups[name].append(url)
        except:
            pass
    
    def better_first(url):
        u = url.lower()
        return (u.endswith('.m3u8') or 'hd' in u or '1080' in u)
    
    all_channels = []
    for name, urls in groups.items():
        urls = list(dict.fromkeys(urls))
        urls.sort(key=lambda x: not better_first(x))
        all_channels.append({
            'name': name,
            'url': urls[0],
            'streams': len(urls),
            'fusion': len(urls) > 1,
            'backups': urls
        })
    
    all_channels.sort(key=lambda x: x['name'])
    
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


@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Expose-Headers'] = '*'
    return response


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