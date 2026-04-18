#!/usr/bin/env python3
"""
Scraper de M3U Premium - Fuentes públicas verificadas
Extrae streams de las mejores fuentes gratuitas públicas
"""

import re
import json
import sqlite3
import requests
from bs4 import BeautifulSoup
from db_utils import get_db_path

FUENTES = [
    # iptv-org - La más completa y actualizada
    "https://iptv-org.github.io/iptv/index.m3u",
    # Listas por categoría
    "https://iptv-org.github.io/iptv/categories/movies.m3u",
    "https://iptv-org.github.io/iptv/categories/sports.m3u",
    "https://iptv-org.github.io/iptv/categories/news.m3u",
    "https://iptv-org.github.io/iptv/categories/entertainment.m3u",
    "https://iptv-org.github.io/iptv/categories/kids.m3u",
    "https://iptv-org.github.io/iptv/categories/music.m3u",
    # Listas por país - Latinoamerica
    "https://iptv-org.github.io/iptv/countries/mx.m3u",
    "https://iptv-org.github.io/iptv/countries/ar.m3u",
    "https://iptv-org.github.io/iptv/countries/co.m3u",
    "https://iptv-org.github.io/iptv/countries/cl.m3u",
    "https://iptv-org.github.io/iptv/countries/pe.m3u",
    "https://iptv-org.github.io/iptv/countries/br.m3u",
    "https://iptv-org.github.io/iptv/countries/ve.m3u",
    "https://iptv-org.github.io/iptv/countries/ec.m3u",
    "https://iptv-org.github.io/iptv/countries/gt.m3u",
    "https://iptv-org.github.io/iptv/countries/sv.m3u",
    "https://iptv-org.github.io/iptv/countries/hn.m3u",
    "https://iptv-org.github.io/iptv/countries/cr.m3u",
    "https://iptv-org.github.io/iptv/countries/pa.m3u",
    # Europa
    "https://iptv-org.github.io/iptv/countries/es.m3u",
    "https://iptv-org.github.io/iptv/countries/us.m3u",
    "https://iptv-org.github.io/iptv/countries/uk.m3u",
    "https://iptv-org.github.io/iptv/countries/de.m3u",
    "https://iptv-org.github.io/iptv/countries/fr.m3u",
    "https://iptv-org.github.io/iptv/countries/it.m3u",
    "https://iptv-org.github.io/iptv/countries/pt.m3u",
    "https://iptv-org.github.io/iptv/countries/pl.m3u",
    "https://iptv-org.github.io/iptv/countries/ru.m3u",
]

def get_db():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def parse_m3u(content, source_name):
    """Parse M3U content and extract streams"""
    streams = []
    lines = content.split('\n')
    
    current_info = {}
    
    for line in lines:
        line = line.strip()
        
        if line.startswith('#EXTINF:'):
            # Extraer información del canal
            # Formato: #EXTINF:-1 tvg-id="..." tvg-name="..." group-title="...",Canal Name
            match = re.search(r'tvg-name="([^"]*)"', line)
            name = match.group(1) if match else None
            
            match_group = re.search(r'group-title="([^"]*)"', line)
            group = match_group.group(1) if match_group else None
            
            if not name:
                # Buscar después de la coma
                parts = line.split(',')
                if len(parts) > 1:
                    name = parts[1].strip()
            
            current_info = {
                'name': name or 'Unknown',
                'group': group or 'General'
            }
            
        elif line.startswith('http') and current_info.get('name'):
            # Es una URL de stream
            streams.append({
                'url': line,
                'name': current_info['name'],
                'group': current_info['group'],
                'source': source_name
            })
            current_info = {}
    
    return streams

def fetch_m3u(url):
    """Descarga una lista M3U"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.text
    except Exception as e:
        print(f"  Error descargando {url}: {e}")
    return None

def get_category_from_group(group):
    """Determina la categoría basándose en el group-title"""
    group_lower = (group or '').lower()
    
    if any(x in group_lower for x in ['movie', 'cine', 'film']):
        return 'Cine'
    elif any(x in group_lower for x in ['sport', 'deporte', 'futbol', 'football']):
        return 'Deportes'
    elif any(x in group_lower for x in ['news', 'noticia']):
        return 'Noticias'
    elif any(x in group_lower for x in ['kids', 'child', 'anime', 'cartoon']):
        return 'Infantil'
    elif any(x in group_lower for x in ['music', 'musica']):
        return 'Musica'
    elif any(x in group_lower for x in ['doc', 'science', 'nature', 'history']):
        return 'Documental'
    elif any(x in group_lower for x in ['entertainment', 'series', 'tv']):
        return 'Entretenimiento'
    return 'General'

def add_to_database(streams):
    """Agrega streams a la base de datos"""
    conn = get_db()
    cursor = conn.cursor()
    
    added_streams = 0
    added_channels = 0
    
    # Agrupar por nombre de canal
    channel_streams = {}
    for stream in streams:
        name = stream['name']
        if name not in channel_streams:
            channel_streams[name] = []
        channel_streams[name].append(stream)
    
    # Agregar cada stream individual
    for stream in streams:
        url = stream['url']
        name = stream['name']
        group = stream['group']
        
        if not url or not name or len(name) < 2:
            continue
        
        # Determinar categoría
        category = get_category_from_group(group)
        
        # Insertar stream
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO streams (url, channel, country, status, latency, score)
                VALUES (?, ?, 'PUBLIC', 'unknown', 999, 0)
            """, (url, name))
            added_streams += 1
        except:
            pass
        
        # Insertar o actualizar canal
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO channels (name, category, stream_count)
                VALUES (?, ?, 0)
            """, (name, category))
            if cursor.rowcount > 0:
                added_channels += 1
        except:
            pass
    
    conn.commit()
    conn.close()
    
    return added_streams, added_channels

def main():
    print("=" * 60)
    print("SCRAPER M3U PREMIUM - FUENTES PÚBLICAS")
    print("=" * 60)
    
    all_streams = []
    
    for url in FUENTES:
        print(f"\n[Descargando] {url}")
        content = fetch_m3u(url)
        
        if content:
            streams = parse_m3u(content, url.split('/')[-1])
            print(f"  -> {len(streams)} streams encontrados")
            all_streams.extend(streams)
        else:
            print(f"  -> Error o timeout")
    
    print(f"\n[TOTAL] {len(all_streams)} streams recopilados")
    
    # Deduplicar por URL
    seen_urls = set()
    unique_streams = []
    for s in all_streams:
        if s['url'] not in seen_urls:
            seen_urls.add(s['url'])
            unique_streams.append(s)
    
    print(f"[ÚNICOS] {len(unique_streams)} streams sin duplicar")
    
    # Agregar a BD
    if unique_streams:
        streams_added, channels_added = add_to_database(unique_streams)
        print(f"\n[BD] {streams_added} streams agregados")
        print(f"[BD] {channels_added} canales registrados")
    
    print("\n" + "=" * 60)
    print("COMPLETADO")
    print("=" * 60)

if __name__ == '__main__':
    main()