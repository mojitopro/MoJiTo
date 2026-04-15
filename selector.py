import sqlite3
import os
import time
import requests

DB_PATH = os.environ.get('DB_PATH', 'streams.db')

def get_all_channels():
    db_path = os.environ.get('DB_PATH', 'streams.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, category, stream_count FROM channels ORDER BY name")
    channels = []
    for r in cursor.fetchall():
        name = r[1] or ''
        category = r[2] or auto_categorize(name)
        channels.append({'id': r[0], 'name': name, 'category': category, 'streams': r[3]})
    return channels

def auto_categorize(name):
    """Categoriza un canal por su nombre"""
    name_lower = name.lower()
    if any(x in name_lower for x in ['espn', 'sports', 'tudn', 'futbol', 'fox sports']):
        return 'Deportes'
    if any(x in name_lower for x in ['hbo', 'cinemax', 'showtime', 'movie', 'cine']):
        return 'Cine'
    if any(x in name_lower for x in ['cnn', 'bbc', 'news', 'telesur', 'dw']):
        return 'Noticias'
    if any(x in name_lower for x in ['azteca', 'estrellas', 'canal 5', 'televisa']):
        return 'Mexico'
    if any(x in name_lower for x in ['trece', 'telefe', 'america tv']):
        return 'Argentina'
    if any(x in name_lower for x in ['tvn', 'canal 13', 'chile']):
        return 'Chile'
    if any(x in name_lower for x in ['caracol', 'rcn']):
        return 'Colombia'
    if any(x in name_lower for x in ['la 1', 'antena', 'tve', 'espana']):
        return 'Espana'
    if any(x in name_lower for x in ['cartoon', 'nick', 'disney', 'kids']):
        return 'Infantil'
    if any(x in name_lower for x in ['discovery', 'history', 'nat geo', 'animal']):
        return 'Documental'
    if any(x in name_lower for x in ['mt', 'vh1', 'musica']):
        return 'Musica'
    if any(x in name_lower for x in ['fox', 'warner', 'universal', 'sony', 'adult']):
        return 'Entretenimiento'
    return 'General'

def get_channel_streams(channel):
    """Obtiene TODOS los streams de un canal para redundancia"""
    db_path = os.environ.get('DB_PATH', 'streams.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    streams = []
    
    # Buscar por nombre exacto
    cursor.execute("""
        SELECT url, latency, failures, last_check, score 
        FROM streams 
        WHERE LOWER(channel) = LOWER(?)
        ORDER BY score DESC, latency ASC, failures ASC
    """, (channel,))
    
    for r in cursor.fetchall():
        streams.append({
            'url': r[0],
            'latency': r[1],
            'failures': r[2],
            'last_check': r[3],
            'score': r[4]
        })
    
    # Si no hay, buscar por similitud
    if not streams:
        cursor.execute("""
            SELECT url, latency, failures, last_check, score 
            FROM streams 
            WHERE LOWER(channel) LIKE ?
            ORDER BY score DESC, latency ASC, failures ASC
            LIMIT 20
        """, (f'%{channel.lower()}%',))
        
        for r in cursor.fetchall():
            streams.append({
                'url': r[0],
                'latency': r[1],
                'failures': r[2],
                'last_check': r[3],
                'score': r[4]
            })
    
    conn.close()
    return streams

def get_best_stream(channel, max_retries=3, validate=False):
    """
    Obtiene el mejor stream con redundancia automatica.
    Si validate=True, prueba streams reales. Si no, usa el score.
    """
    streams = get_channel_streams(channel)
    
    if not streams:
        return None
    
    # Si no hay streams en DB, buscar directo
    if validate:
        return _validate_streams(channel, streams, max_retries)
    
    # Solo retornar el primero (mas alto score)
    best = streams[0]
    return {
        'url': best['url'],
        'channel': channel,
        'latency': best['latency'],
        'failures': best['failures']
    }

def _validate_streams(channel, streams, max_retries=3):
    """Valida streams reales"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': '*/*',
    }
    
    checked = 0
    for stream in streams:
        if checked >= max_retries:
            break
        
        url = stream['url']
        if not url or len(url) < 10:
            continue
        
        if any(x in url.lower() for x in ['youtube.com', 'youtu.be', '.mp4', '.avi', '.mkv']):
            continue
        
        try:
            start = time.time()
            r = requests.head(url, timeout=3, allow_redirects=True, headers=headers)
            latency_ms = int((time.time() - start) * 1000)
            
            if r.status_code == 200:
                ct = r.headers.get('Content-Type', '').lower()
                if any(t in ct for t in ['video', 'application', 'stream', 'mpeg', 'mp4', 'octet', 'x-mpegurl', 'vnd.apple']):
                    r.close()
                    update_stream_score(url, latency_ms, success=True)
                    return {
                        'url': url,
                        'channel': channel,
                        'latency': latency_ms,
                        'failures': stream['failures']
                    }
            r.close()
        except:
            pass
        
        checked += 1
        update_stream_score(url, 0, success=False)
    
    return None

def update_stream_score(url, latency, success):
    """Actualiza el score de un stream"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        now = int(time.time())
        
        if success:
            cursor.execute("""
                UPDATE streams 
                SET status='online', latency=?, last_check=?, 
                    failures=0, score = score + 1
                WHERE url=?
            """, (latency, now, url))
        else:
            cursor.execute("""
                UPDATE streams 
                SET status='offline', failures = failures + 1, 
                    last_check=?, score = MAX(0, score - 0.5)
                WHERE url=?
            """, (now, url))
        
        conn.commit()
        conn.close()
    except:
        pass

def search_channels(query):
    """Busca canales por nombre"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, name, category, stream_count 
        FROM channels 
        WHERE LOWER(name) LIKE ?
        ORDER BY stream_count DESC, name
        LIMIT 50
    """, (f'%{query.lower()}%',))
    
    results = [{'id': r[0], 'name': r[1], 'category': r[2], 'streams': r[3]} for r in cursor.fetchall()]
    conn.close()
    return results

def get_category_channels(category):
    """Obtiene canales de una categoria"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, name, category, stream_count 
        FROM channels 
        WHERE LOWER(category) LIKE ?
        ORDER BY name
    """, (f'%{category.lower()}%',))
    
    results = [{'id': r[0], 'name': r[1], 'category': r[2], 'streams': r[3]} for r in cursor.fetchall()]
    conn.close()
    return results

def get_stats():
    """Obtiene estadisticas de la DB"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM streams")
    total_streams = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM streams WHERE status='online'")
    online_streams = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM channels")
    total_channels = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM channels WHERE stream_count > 1")
    redundant_channels = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'total_streams': total_streams,
        'online_streams': online_streams,
        'total_channels': total_channels,
        'redundant_channels': redundant_channels
    }

if __name__ == '__main__':
    import json
    print(json.dumps(get_stats(), indent=2))
