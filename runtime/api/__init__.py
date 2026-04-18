from flask import Flask, jsonify, request, send_file
from pathlib import Path


app = Flask(__name__)


def get_db():
    from runtime.db import Database
    return Database()


def wants_premium_only():
    category = request.args.get('category', '').strip().lowet()
    premium_flag = request.args.get('premium', '').strip().lower()
    mode = request.args.get('mode', '').strip().lower()
    
    if category in {'premium', 'on-demand', 'ondemand', 'vod'}:
        return True
    if premium_flag in {'1', 'true', 'yes', 'on'}:
        return True
    if mode in {'premium', 'on-demand', 'ondemand'}:
        return True
    return False


@app.route('/')
def index():
    from pathlib import Path
    BASE_DIR = Path(__file__).parent.parent
    return send_file(str(BASE_DIR / 'tv.html'))


@app.route('/tv')
@app.route('/tv.html')
def tv():
    return index()


@app.route('/api/channels')
def api_channels():
    db = get_db()
    limit = request.args.get('limit', type=int)
    premium_only = wants_premium_only()
    
    channels = []
    for cluster in db.get_all_clusters():
        if premium_only and 'premium' not in (cluster.canonical_name or '').lower():
            continue
        
        streams = db.get_cluster_streams(cluster.cluster_id)
        if streams:
            channels.append({
                'cluster_id': cluster.cluster_id,
                'name': cluster.canonical_name,
                'confidence': cluster.confidence,
                'stream_count': len(streams)
            })
    
    if limit:
        channels = channels[:limit]
    
    return jsonify({
        'status': 'ok',
        'channels': channels,
    })


@app.route('/api/stream/<path:channel>')
@app.route('/api/channel/<path:channel>')
def api_stream(channel):
    from runtime.utils import normalize_channel_name
    
    db = get_db()
    normalized = normalize_channel_name(channel)
    
    best_stream = None
    fallbacks = []
    
    for cluster in db.get_all_clusters():
        if cluster.canonical_name == normalized:
            streams = db.get_cluster_streams(cluster.cluster_id)
            
            if streams:
                for cs in streams:
                    if cs.is_primary:
                        best_stream = cs.stream_url
                    else:
                        fallbacks.append(cs.stream_url)
            
            fusion = db.get_fusion_state(cluster.cluster_id)
            if fusion and fusion.active_stream:
                best_stream = fusion.active_stream
            
            break
    
    if best_stream:
        return jsonify({
            'status': 'ok',
            'stream': best_stream,
            'fallbacks': fallbacks,
            'url': best_stream
        })
    
    return jsonify({
        'status': 'error',
        'error': 'channel not found',
        'url': None,
        'fallbacks': []
    })


@app.route('/api/cluster/<cluster_id>')
def api_cluster(cluster_id):
    db = get_db()
    
    cluster = db.get_cluster(cluster_id)
    if not cluster:
        return jsonify({'status': 'error', 'error': 'cluster not found'})
    
    streams = db.get_cluster_streams(cluster_id)
    fusion = db.get_fusion_state(cluster_id)
    
    return jsonify({
        'status': 'ok',
        'cluster': {
            'cluster_id': cluster.cluster_id,
            'canonical_name': cluster.canonical_name,
            'confidence': cluster.confidence,
        },
        'streams': [{
            'url': cs.stream_url,
            'priority': cs.priority,
            'is_primary': cs.is_primary,
            'last_check': cs.last_check
        } for cs in streams],
        'fusion': {
            'active_stream': fusion.active_stream if fusion else None,
            'switch_count': fusion.switch_count if fusion else 0,
            'last_switch': fusion.last_switch if fusion else 0
        } if fusion else None
    })


@app.route('/api/metrics/<path:url>')
def api_metrics(url):
    from urllib.parse import unquote
    url = unquote(url)
    
    db = get_db()
    metrics = db.get_stream_metrics(url)
    
    if metrics:
        return jsonify({
            'status': 'ok',
            'metrics': {
                'startup_time': metrics.startup_time,
                'freeze_count': metrics.freeze_count,
                'freeze_duration': metrics.freeze_duration,
                'avg_frame_delta': metrics.avg_frame_delta,
                'black_ratio': metrics.black_ratio,
                'motion_score': metrics.motion_score,
                'stability': metrics.stability,
                'last_check': metrics.last_check
            }
        })
    
    return jsonify({
        'status': 'error',
        'error': 'no metrics found'
    })


@app.route('/api/stats')
def api_stats():
    db = get_db()
    stats = db.get_stats()
    
    return jsonify({
        'status': 'ok',
        'stats': stats
    })


@app.route('/api/search')
def api_search():
    from runtime.utils import normalize_channel_name, string_similarity
    
    q = request.args.get('q', '').strip().lower()
    if not q:
        return jsonify({'status': 'ok', 'streams': []})
    
    db = get_db()
    results = []
    
    for cluster in db.get_all_clusters():
        sim = string_similarity(q, cluster.canonical_name)
        if sim > 0.5:
            streams = db.get_cluster_streams(cluster.cluster_id)
            results.append({
                'cluster_id': cluster.cluster_id,
                'name': cluster.canonical_name,
                'similarity': sim,
                'streams': [cs.stream_url for cs in streams]
            })
    
    results.sort(key=lambda x: x['similarity'], reverse=True)
    
    return jsonify({
        'status': 'ok',
        'streams': results[:20]
    })


@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'mojito-api'})


def run(port=8080):
    app.run(host='0.0.0.0', port=port, threaded=True, debug=False)


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8080))
    run(port)