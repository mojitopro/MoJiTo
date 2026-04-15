import sqlite3
import os
import time

DB_PATH = os.environ.get('DB_PATH', 'streams.db')

def get_all_channels():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, category, best_url FROM channels ORDER BY name")
    
    channels = []
    for r in cursor.fetchall():
        name = r[0] or ''
        category = r[1] or auto_categorize(name)
        best_url = r[2] or ''
        
        # Count streams from streams table
        cursor.execute(
            "SELECT COUNT(*) FROM streams WHERE LOWER(channel) = LOWER(?)",
            (name,)
        )
        stream_cnt = cursor.fetchall()[0][0]
        
        # Count URLs in best_url if pipe-separated
        url_cnt = len(best_url.split('|')) if best_url else 0
        total = max(stream_cnt, url_cnt)
        
        channels.append({
            'name': name,
            'category': category,
            'streams': total
        })
    
    conn.close()
    return channels

def auto_categorize(name):
    name_lower = name.lower()
    if any(x in name_lower for x in ['espn', 'sports', 'tudn', 'futbol', 'fox sports', 'bein']):
        return 'Deportes'
    if any(x in name_lower for x in ['hbo', 'cinemax', 'showtime', 'movie', 'cine', 'star']):
        return 'Cine'
    if any(x in name_lower for x in ['cnn', 'bbc', 'news', 'telesur', 'dw', 'aljazeera']):
        return 'Noticias'
    if any(x in name_lower for x in ['azteca', 'estrellas', 'canal 5', 'televisa', 'mexico']):
        return 'Mexico'
    if any(x in name_lower for x in ['trece', 'telefe', 'argentina', 'tyc', 'america tv']):
        return 'Argentina'
    if any(x in name_lower for x in ['la 1', 'antena', 'tve', 'espana', 'telecinco', 'cuatro']):
        return 'Espana'
    if any(x in name_lower for x in ['cartoon', 'nick', 'disney', 'kids', 'nickelodeon']):
        return 'Infantil'
    if any(x in name_lower for x in ['mt', 'vh1', 'musica', 'telefe']):
        return 'Musica'
    if any(x in name_lower for x in ['discovery', 'history', 'nat geo', 'animal', 'smithsonian']):
        return 'Documental'
    if any(x in name_lower for x in ['fox', 'warner', 'universal', 'sony', 'adult', 'paramount']):
        return 'Entretenimiento'
    return 'General'

def get_all_streams_for_channel(channel_name):
    """Obtiene TODOS los streams disponibles para un canal desde cualquier fuente"""
    all_urls = []
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Streams desde tabla streams (prioridad por score)
    cursor.execute("""
        SELECT url, score, latency, status
        FROM streams 
        WHERE LOWER(channel) = LOWER(?)
        ORDER BY 
            CASE status WHEN 'online' THEN 1 WHEN 'unknown' THEN 2 ELSE 3 END,
            score DESC,
            latency ASC
    """, (channel_name,))
    
    for r in cursor.fetchall():
        url = r[0]
        if url and url not in all_urls:
            all_urls.append({
                'url': url,
                'source': 'db',
                'score': r[1] or 0,
                'latency': r[2] or 999,
                'status': r[3]
            })
    
    # 2. URLs desde best_url en channels (puede tener pipes)
    cursor.execute(
        "SELECT best_url FROM channels WHERE LOWER(name) = LOWER(?)",
        (channel_name,)
    )
    row = cursor.fetchone()
    if row and row[0]:
        for url in row[0].split('|'):
            url = url.strip()
            if url and url not in [u['url'] for u in all_urls]:
                all_urls.append({
                    'url': url,
                    'source': 'best_url',
                    'score': 0,
                    'latency': 999,
                    'status': 'unknown'
                })
    
    # 3. Busqueda fuzzy si no hay resultados
    if not all_urls:
        cursor.execute("""
            SELECT url, score, latency, status
            FROM streams 
            WHERE LOWER(channel) LIKE LOWER(?)
            ORDER BY score DESC
            LIMIT 20
        """, (f'%{channel_name}%',))
        
        for r in cursor.fetchall():
            url = r[0]
            if url and url not in [u['url'] for u in all_urls]:
                all_urls.append({
                    'url': url,
                    'source': 'search',
                    'score': r[1] or 0,
                    'latency': r[2] or 999,
                    'status': r[3]
                })
    
    conn.close()
    return all_urls

def get_best_stream(channel_name, max_retries=3):
    """
    Obtiene el mejor stream con redundancia completa.
    Retorna: {url, fallbacks[], source}
    """
    streams = get_all_streams_for_channel(channel_name)
    
    if not streams:
        return None
    
    # Filtrar URLs invalidas
    valid = []
    skip = ['youtube.com', 'youtu.be', '.mp4', '.avi', '.mkv', '.zip']
    for s in streams:
        if not s['url'] or len(s['url']) < 10:
            continue
        if any(x in s['url'].lower() for x in skip):
            continue
        valid.append(s)
    
    if not valid:
        return None
    
    # Ordenar: online primero, luego por score
    def sort_key(s):
        status_order = {'online': 0, 'unknown': 1, 'offline': 2, 'error': 3, 'timeout': 4, 'not_found': 5}
        so = status_order.get(s['status'], 1)
        return (so, -s['score'], s['latency'])
    
    valid.sort(key=sort_key)
    
    # Mejor stream
    best = valid[0]
    
    # Fallbacks (hasta 8)
    fallbacks = [s['url'] for s in valid[1:9] if s['url'] != best['url']]
    
    return {
        'url': best['url'],
        'channel': channel_name,
        'fallbacks': fallbacks,
        'total_available': len(valid),
        'best_status': best['status']
    }

def search_channels(query):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT DISTINCT name, category
        FROM channels 
        WHERE LOWER(name) LIKE LOWER(?)
        ORDER BY name
        LIMIT 50
    """, (f'%{query}%',))
    
    results = []
    for r in cursor.fetchall():
        name = r[0]
        cursor.execute(
            "SELECT COUNT(*) FROM streams WHERE LOWER(channel) = LOWER(?)",
            (name,)
        )
        cnt = cursor.fetchone()[0]
        results.append({
            'name': name,
            'category': r[1] or auto_categorize(name),
            'streams': cnt
        })
    
    conn.close()
    return results

def get_stats():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM channels")
    total_channels = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM streams")
    total_streams = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM streams WHERE status = 'online'")
    online = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT LOWER(channel)) FROM streams WHERE status = 'online'")
    channels_with_online = cursor.fetchone()[0] or 0
    
    cursor.execute("""
        SELECT COUNT(*) FROM channels 
        WHERE best_url LIKE '%|%'
    """)
    multi_url = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'total_channels': total_channels,
        'total_streams': total_streams,
        'online_streams': online,
        'channels_with_online': channels_with_online,
        'channels_with_redundancy': multi_url
    }

if __name__ == '__main__':
    import json
    print(json.dumps(get_stats(), indent=2))
