import os
import sqlite3
from collections import defaultdict

from channel_utils import (
    is_premium_channel,
    normalize_channel_name,
    normalize_latency_ms,
    stream_sort_key,
)
from db_utils import get_db_path

DB_PATH = get_db_path()


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def auto_categorize(name):
    name_lower = (name or '').lower()
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


def _channel_label(name, category=None):
    normalized = normalize_channel_name(name)
    if is_premium_channel(normalized, category):
        return 'premium'
    return category or auto_categorize(normalized or name)


def _load_all_streams(query=None, premium_only=False, include_unknown=False):
    conn = _connect()
    cursor = conn.cursor()

    clauses = [
        "url IS NOT NULL",
        "url != ''",
        "channel IS NOT NULL",
        "channel != ''",
    ]
    params = []

    if not include_unknown:
        clauses.append("LOWER(status) = 'online'")

    if query:
        clauses.append("LOWER(channel) LIKE LOWER(?)")
        params.append(f"%{query}%")

    sql = f"""
        SELECT channel, url, status, latency, score
        FROM streams
        WHERE {' AND '.join(clauses)}
        ORDER BY
            CASE LOWER(status)
                WHEN 'online' THEN 1
                WHEN 'unknown' THEN 2
                ELSE 3
            END,
            score DESC,
            latency ASC
    """
    cursor.execute(sql, params)

    candidates = []
    seen_urls = set()
    for row in cursor.fetchall():
        url = row['url'] or ''
        if not url or url in seen_urls:
            continue

        channel = row['channel'] or ''
        normalized = normalize_channel_name(channel)
        if not normalized or normalized in {'discovered', 'unknown'}:
            continue

        premium = is_premium_channel(channel) or is_premium_channel(normalized)
        if premium_only and not premium:
            continue

        seen_urls.add(url)
        candidates.append({
            'channel': channel,
            'name': normalized,
            'title': channel,
            'url': url,
            'status': row['status'] or 'unknown',
            'latency': float(row['latency'] or 999),
            'latency_ms': normalize_latency_ms(row['latency']),
            'score': float(row['score'] or 0),
            'category': 'premium' if premium else auto_categorize(normalized),
            'premium': premium,
        })

    conn.close()
    return candidates


def _summarize_group(name, items):
    items = sorted(items, key=stream_sort_key)
    best = items[0]
    fallbacks = [s['url'] for s in items[1:9] if s['url'] != best['url']]
    return {
        'name': name,
        'category': 'premium',
        'streams': len(items),
        'best_url': best['url'],
        'best_latency': best['latency'],
        'best_latency_ms': best.get('latency_ms') or normalize_latency_ms(best['latency']),
        'best_score': best['score'],
        'best_status': best['status'],
        'fallbacks': fallbacks,
        'premium': True,
    }


def get_premium_channels(limit=None, sort_by='latency'):
    candidates = _load_all_streams(premium_only=True)
    grouped = defaultdict(list)

    for item in candidates:
        key = item['name']
        grouped[key].append(item)

    channels = [_summarize_group(name, items) for name, items in grouped.items() if items]

    if sort_by == 'name':
        channels.sort(key=lambda c: c['name'])
    else:
        channels.sort(key=lambda c: (
            c.get('best_latency_ms') is None,
            c.get('best_latency_ms') or 999999,
            -c['best_score'],
            c['name']
        ))

    if limit:
        channels = channels[:limit]
    return channels


def get_all_channels(limit=None, premium_only=False, sort_by='name'):
    if premium_only:
        return get_premium_channels(limit=limit, sort_by=sort_by)

    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("SELECT name, category, best_url FROM channels ORDER BY name")

    channels = []
    for row in cursor.fetchall():
        name = row['name'] or ''
        if not name:
            continue

        category = row['category'] or auto_categorize(name)
        best_url = row['best_url'] or ''

        cursor.execute(
            "SELECT COUNT(*) FROM streams WHERE LOWER(channel) = LOWER(?)",
            (name,)
        )
        stream_cnt = cursor.fetchone()[0]

        url_cnt = len([u for u in best_url.split('|') if u.strip()]) if best_url else 0
        total = max(stream_cnt, url_cnt)

        channels.append({
            'name': name,
            'category': category,
            'streams': total,
            'best_url': best_url,
            'premium': category == 'premium',
        })

    conn.close()

    if sort_by == 'latency':
        channels.sort(key=lambda c: c['name'])
    else:
        channels.sort(key=lambda c: c['name'])

    if limit:
        channels = channels[:limit]
    return channels


def get_best_stream(channel_name, max_retries=3, premium_only=False):
    """
    Returns the best stream for a channel, with fallbacks.
    """
    query = normalize_channel_name(channel_name) or (channel_name or '').strip()
    if not query:
        return None

    candidates = _load_all_streams(query=query, premium_only=premium_only, include_unknown=False)

    if not candidates:
        # Fallback to the channels table if we do not have direct stream matches.
        conn = _connect()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, best_url, category FROM channels WHERE LOWER(name) LIKE LOWER(?) ORDER BY name LIMIT 20",
            (f'%{query}%',)
        )
        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            best_url = row['best_url'] or ''
            if not best_url:
                continue
            if premium_only and not is_premium_channel(row['name'], row['category']):
                continue

            for url in [u.strip() for u in best_url.split('|') if u.strip()]:
                candidates.append({
                    'channel': row['name'],
                    'name': normalize_channel_name(row['name']) or row['name'],
                    'title': row['name'],
                    'url': url,
                    'status': 'unknown',
                    'latency': 999,
                    'latency_ms': None,
                    'score': 0,
                    'category': 'premium' if is_premium_channel(row['name'], row['category']) else (row['category'] or auto_categorize(row['name'])),
                    'premium': is_premium_channel(row['name'], row['category']),
                })

    if not candidates:
        return None

    candidates = sorted(candidates, key=stream_sort_key)
    best = candidates[0]
    fallbacks = [s['url'] for s in candidates[1:9] if s['url'] != best['url']]

    return {
        'url': best['url'],
        'channel': channel_name,
        'fallbacks': fallbacks,
        'total_available': len(candidates),
        'best_status': best['status'],
        'best_latency': best['latency'],
        'best_latency_ms': best.get('latency_ms') or normalize_latency_ms(best['latency']),
        'best_score': best['score'],
        'category': best['category'],
        'premium': best['premium'],
    }


def search_channels(query, premium_only=False, limit=50):
    """
    Returns stream candidates for the search UI.
    """
    q = (query or '').strip()
    if not q:
        return []

    candidates = _load_all_streams(query=q, premium_only=premium_only, include_unknown=False)
    if not candidates:
        return []

    candidates = sorted(candidates, key=stream_sort_key)

    results = []
    seen_urls = set()
    for item in candidates:
        if item['url'] in seen_urls:
            continue
        seen_urls.add(item['url'])
        results.append({
            'title': item['title'],
            'url': item['url'],
            'channel': item['channel'],
            'latency': item['latency'],
            'latency_ms': item.get('latency_ms'),
            'score': item['score'],
            'status': item['status'],
            'category': item['category'],
            'premium': item['premium'],
        })
        if len(results) >= limit:
            break

    return results


def get_stats():
    conn = _connect()
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

    premium_channels = len(get_premium_channels(limit=None, sort_by='latency'))
    premium_streams = len(_load_all_streams(premium_only=True))

    conn.close()

    return {
        'total_channels': total_channels,
        'total_streams': total_streams,
        'online_streams': online,
        'channels_with_online': channels_with_online,
        'channels_with_redundancy': multi_url,
        'premium_channels': premium_channels,
        'premium_streams': premium_streams,
    }


if __name__ == '__main__':
    import json

    print(json.dumps(get_stats(), indent=2))
