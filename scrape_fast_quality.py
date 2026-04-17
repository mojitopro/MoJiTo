#!/usr/bin/env python3
"""
SCRAPER DE STREAMS DE ALTA CALIDAD - FAST SERVICES
Plex, Pluto TV, Samsung TV Plus, Roku, Tubi
Estas son fuentes LEGALES y de ALTA CALIDAD
"""

import re
import json
import sqlite3
import requests
from db_utils import get_db_path

# URLs de los M3U de mejor calidad - FAST Channels
FUENTES_FAST = [
    # Plex TV - Excelente calidad HD
    "https://raw.githubusercontent.com/BuddyChewChew/app-m3u-generator/main/playlists/plex_all.m3u",
    "https://raw.githubusercontent.com/BuddyChewChew/app-m3u-generator/main/playlists/plex_us.m3u",
    "https://raw.githubusercontent.com/BuddyChewChew/app-m3u-generator/main/playlists/plex_mx.m3u",
    
    # Pluto TV - Muy buena calidad
    "https://raw.githubusercontent.com/BuddyChewChew/app-m3u-generator/main/playlists/plutotv_all.m3u",
    "https://raw.githubusercontent.com/BuddyChewChew/app-m3u-generator/main/playlists/plutotv_us.m3u",
    "https://raw.githubusercontent.com/BuddyChewChew/app-m3u-generator/main/playlists/plutotv_mx.m3u",
    "https://raw.githubusercontent.com/BuddyChewChew/app-m3u-generator/main/playlists/plutotv_es.m3u",
    
    # Samsung TV Plus
    "https://raw.githubusercontent.com/BuddyChewChew/app-m3u-generator/main/playlists/samsungtvplus_all.m3u",
    "https://raw.githubusercontent.com/BuddyChewChew/app-m3u-generator/main/playlists/samsungtvplus_us.m3u",
    
    # Roku
    "https://raw.githubusercontent.com/BuddyChewChew/app-m3u-generator/main/playlists/roku_all.m3u",
    
    # Tubi TV
    "https://raw.githubusercontent.com/BuddyChewChew/app-m3u-generator/main/playlists/tubi_all.m3u",
    
    # Free-TV/IPTV - HD-first, calidad sobre cantidad
    "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8",
]

def get_db():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn

def fetch_m3u(url):
    """Descarga M3U"""
    try:
        resp = requests.get(url, timeout=20, headers={
            'User-Agent': 'Mozilla/5.0 (Smart TV)'
        })
        if resp.status_code == 200:
            return resp.text
    except Exception as e:
        print(f"  Error: {e}")
    return None

def parse_m3u(content, fuente):
    """Parsea M3U y extrae streams"""
    streams = []
    lines = content.split('\n')
    info = {}
    
    for line in lines:
        line = line.strip()
        
        if line.startswith('#EXTINF:'):
            # Extraer metadatos
            info = {
                'name': 'Unknown',
                'group': 'General',
                'logo': '',
                'quality': 'HD'
            }
            
            # tvg-name
            m = re.search(r'tvg-name="([^"]*)"', line)
            if m: info['name'] = m.group(1)
            
            # group-title  
            m = re.search(r'group-title="([^"]*)"', line)
            if m: info['group'] = m.group(1)
            
            # tvg-logo
            m = re.search(r'tvg-logo="([^"]*)"', line)
            if m: info['logo'] = m.group(1)
            
            # Buscar nombre después de la coma
            if info['name'] == 'Unknown' and ',' in line:
                info['name'] = line.split(',')[-1].strip()
        
        elif line.startswith('http') and info.get('name'):
            # Es un stream
            streams.append({
                'url': line,
                'name': info['name'],
                'group': info.get('group', 'General'),
                'logo': info.get('logo', ''),
                'source': fuente.split('/')[-1].replace('.m3u', '').replace('_', ' ').title()
            })
            info = {}
    
    return streams

def categorize(group, name):
    """Categoriza el canal"""
    g = (group or '').lower()
    n = (name or '').lower()
    
    if any(x in g+n for x in ['movie', 'cine', 'film', 'drama']):
        return 'Cine'
    elif any(x in g+n for x in ['sport', 'deporte', 'futbol', 'football', 'nba', 'nfl']):
        return 'Deportes'
    elif any(x in g+n for x in ['news', 'noticia', 'newscast']):
        return 'Noticias'
    elif any(x in g+n for x in ['kids', 'child', 'anime', 'cartoon', 'animation']):
        return 'Infantil'
    elif any(x in g+n for x in ['music', 'musica', 'concert']):
        return 'Musica'
    elif any(x in g+n for x in ['doc', 'science', 'nature', 'history', 'travel']):
        return 'Documental'
    elif any(x in g+n for x in ['comedy', 'entertainment', 'series', 'tv', 'show']):
        return 'Entretenimiento'
    return 'General'

def save_to_db(streams):
    """Guarda en base de datos"""
    conn = get_db()
    cur = conn.cursor()
    
    # Agrupar por URL única
    seen_urls = set()
    streams_added = 0
    channels_added = 0
    
    for s in streams:
        url = s['url']
        if url in seen_urls:
            continue
        seen_urls.add(url)
        
        name = s['name']
        if not name or len(name) < 2:
            continue
        
        category = categorize(s['group'], s['name'])
        
        # Insertar stream
        try:
            cur.execute("""
                INSERT OR REPLACE INTO streams (url, channel, country, status, latency, score)
                VALUES (?, ?, 'FAST', 'unknown', 999, 0.5)
            """, (url, name))
            streams_added += 1
        except: pass
        
        # Insertar canal
        try:
            cur.execute("""
                INSERT OR IGNORE INTO channels (name, category, stream_count)
                VALUES (?, ?, 0)
            """, (name, category))
            if cur.rowcount > 0:
                channels_added += 1
        except: pass
    
    conn.commit()
    conn.close()
    return streams_added, channels_added

def main():
    print("=" * 60)
    print("SCRAPER FAST CHANNELS - CALIDAD PREMIUM")
    print("Plex | Pluto TV | Samsung Plus | Roku | Tubi")
    print("=" * 60)
    
    all_streams = []
    
    for url in FUENTES_FAST:
        print(f"\n[Descargando] {url}")
        content = fetch_m3u(url)
        
        if content:
            streams = parse_m3u(content, url)
            print(f"  -> {len(streams)} streams")
            all_streams.extend(streams)
        else:
            print(f"  -> Error")
    
    print(f"\n[TOTAL] {len(all_streams)} streams")
    
    # Deduplicar
    unique = []
    seen = set()
    for s in all_streams:
        if s['url'] not in seen:
            seen.add(s['url'])
            unique.append(s)
    
    print(f"[ÚNICOS] {len(unique)} streams")
    
    # Guardar
    if unique:
        s_added, c_added = save_to_db(unique)
        print(f"\n[BD] {s_added} streams, {c_added} canales")
    
    print("\n" + "=" * 60)
    print("COMPLETADO")
    print("=" * 60)

if __name__ == '__main__':
    main()