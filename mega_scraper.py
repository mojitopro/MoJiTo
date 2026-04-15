#!/usr/bin/env python3
"""
MoJiTo MEGA SCRAPER v2 - Compatible con schema existente
Todo lo que existe, sin validacion - la redundancia es la clave
"""

import requests
import sqlite3
import json
import re
import time
import os
from datetime import datetime

DB_PATH = os.environ.get('DB_PATH', 'streams.db')
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': '*/*',
}

MEGA_SOURCES = {
    'iptv_streams': 'https://iptv-org.github.io/api/streams.json',
    'iptv_index': 'https://iptv-org.github.io/iptv/index.m3u',
    'freetv_main': 'https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8',
    'tva_vpn': 'https://tva.org.ua/ip/sam/vpn.m3u',
    'iptv_free_tv': 'https://raw.githubusercontent.com/iptv-free/TV/refs/heads/FREE/TV',
}

def get_m3u_streams(content):
    streams = []
    lines = content.split('\n')
    current_name = ''
    current_country = ''
    
    for line in lines:
        line = line.strip()
        if line.startswith('#EXTINF:'):
            match = re.search(r',(.+)$', line)
            if match:
                current_name = match.group(1).strip()
                current_name = re.sub(r'\[.*?\]', '', current_name).strip()
            
            country_match = re.search(r'tvg-country="([^"]+)"', line)
            if country_match:
                current_country = country_match.group(1)
        elif line.startswith('http') and ('.m3u' in line.lower() or '.ts' in line.lower()):
            streams.append({'url': line, 'name': current_name, 'country': current_country})
        elif line.startswith('rtmp://'):
            streams.append({'url': line, 'name': current_name, 'country': current_country})
    
    return streams

def fetch_source(name, url, timeout=30):
    try:
        r = requests.get(url, timeout=timeout, headers=HEADERS)
        if r.status_code == 200:
            ct = r.headers.get('Content-Type', '')
            if 'json' in ct:
                return {'name': name, 'type': 'json', 'content': r.json()}
            return {'name': name, 'type': 'm3u', 'content': r.text}
    except Exception as e:
        print(f"Error {name}: {e}")
    return None

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS streams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            channel TEXT,
            country TEXT DEFAULT 'UNKNOWN',
            status TEXT DEFAULT 'unknown',
            latency REAL DEFAULT 999,
            failures INTEGER DEFAULT 0,
            last_check INTEGER DEFAULT 0,
            score REAL DEFAULT 0,
            node_ip TEXT
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            stream_count INTEGER DEFAULT 0,
            best_url TEXT,
            category TEXT DEFAULT 'general'
        )
    """)
    
    conn.commit()
    return conn

def save_stream(conn, url, channel, country='UNKNOWN'):
    if not url or not channel or len(url) < 10:
        return False
    
    url = url.strip()
    channel = channel.strip()
    
    if any(x in url.lower() for x in ['youtube.com', 'youtu.be', '.mp4', '.avi', '.mkv']):
        return False
    
    try:
        c = conn.cursor()
        c.execute("""
            INSERT OR IGNORE INTO streams (url, channel, country, status)
            VALUES (?, ?, ?, 'unknown')
        """, (url, channel, country))
        return True
    except:
        return False

def build_channel_catalog(conn):
    """Construye catalogo de canales desde streams"""
    c = conn.cursor()
    
    c.execute("""
        SELECT channel, COUNT(*) as cnt, MIN(url) as first_url
        FROM streams
        WHERE channel IS NOT NULL AND channel != ''
        GROUP BY LOWER(channel)
    """)
    
    for name, cnt, best_url in c.fetchall():
        c.execute("""
            INSERT OR REPLACE INTO channels (name, stream_count, best_url)
            VALUES (?, ?, ?)
        """, (name.strip(), cnt, best_url))
    
    conn.commit()

def main():
    print("="*70)
    print("MOJITO MEGA SCRAPER v2 - TODO LO QUE EXISTE")
    print("="*70)
    print(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    conn = init_db()
    total_added = 0
    sources = 0
    
    # 1. IPTV-org streams.json
    print("\n[1/5] IPTV-org streams.json...")
    data = fetch_source('iptv_org', MEGA_SOURCES['iptv_streams'])
    if data and data['type'] == 'json':
        for item in data['content']:
            url = item.get('url', '')
            title = item.get('title', '')
            if url and '.m3u' in url.lower():
                if save_stream(conn, url, title):
                    total_added += 1
        print(f"  -> {total_added} streams agregados")
        sources += 1
    conn.commit()
    
    # 2. IPTV-org index.m3u
    print("\n[2/5] IPTV-org index.m3u...")
    before = total_added
    data = fetch_source('iptv_org_m3u', MEGA_SOURCES['iptv_index'])
    if data and data['type'] == 'm3u':
        for s in get_m3u_streams(data['content']):
            if save_stream(conn, s['url'], s['name'], s['country']):
                total_added += 1
        print(f"  -> +{total_added - before} streams")
        sources += 1
    conn.commit()
    
    # 3. Free-TV
    print("\n[3/5] Free-TV playlist...")
    before = total_added
    data = fetch_source('freetv', MEGA_SOURCES['freetv_main'])
    if data and data['type'] == 'm3u':
        for s in get_m3u_streams(data['content']):
            if save_stream(conn, s['url'], s['name'], s['country']):
                total_added += 1
        print(f"  -> +{total_added - before} streams")
        sources += 1
    conn.commit()
    
    # 4. TVA
    print("\n[4/5] TVA playlist...")
    before = total_added
    data = fetch_source('tva', MEGA_SOURCES['tva_vpn'])
    if data and data['type'] == 'm3u':
        for s in get_m3u_streams(data['content']):
            if save_stream(conn, s['url'], s['name'], s['country']):
                total_added += 1
        print(f"  -> +{total_added - before} streams")
        sources += 1
    conn.commit()
    
    # 5. IPTV-free
    print("\n[5/5] IPTV-free/TV...")
    before = total_added
    data = fetch_source('iptv_free', MEGA_SOURCES['iptv_free_tv'])
    if data and data['type'] == 'm3u':
        for s in get_m3u_streams(data['content']):
            if save_stream(conn, s['url'], s['name'], s['country']):
                total_added += 1
        print(f"  -> +{total_added - before} streams")
        sources += 1
    conn.commit()
    
    # Deduplicar
    print("\n[+] Deduplicando...")
    c = conn.cursor()
    c.execute("""
        DELETE FROM streams WHERE id NOT IN (
            SELECT MIN(id) FROM streams GROUP BY url
        )
    """)
    conn.commit()
    
    # Construir catalogo
    print("\n[+] Construyendo catalogo de canales...")
    build_channel_catalog(conn)
    
    # Stats
    c.execute("SELECT COUNT(*) FROM streams")
    total_streams = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM channels")
    total_channels = c.fetchone()[0]
    
    print(f"\n{'='*70}")
    print(f"RESULTADO:")
    print(f"  Fuentes: {sources}")
    print(f"  Streams totales: {total_streams}")
    print(f"  Canales unicos: {total_channels}")
    print(f"{'='*70}")
    
    conn.close()
    print("\nListo! Redundancia maneja los streams muertos.")

if __name__ == '__main__':
    main()
