#!/usr/bin/env python3
"""
MAX IPTV 4K - EXTRACCION TOTAL v3
Extrae ABSOLUTAMENTE TODO de la página
"""

import re
import json
import sqlite3
import requests
from bs4 import BeautifulSoup
from db_utils import get_db_path
import time

MAXIPTV_URL = "https://maxiptv4k.com/"

def get_db_connection():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def extract_everything():
    print(f"Extrayendo TODO desde {MAXIPTV_URL}...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml',
    }
    
    all_channels = set()
    all_urls = set()
    
    urls_to_try = [
        MAXIPTV_URL,
        MAXIPTV_URL + "channels-list/",
    ]
    
    for url in urls_to_try:
        print(f"\n[EXPLORANDO] {url}")
        try:
            response = requests.get(url, headers=headers, timeout=30)
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')
            
            # 1. Extraer de todos los enlaces
            print("  - Extrayendo de enlaces...")
            for link in soup.find_all('a'):
                text = link.get_text().strip()
                if text and len(text) > 2 and len(text) < 50:
                    all_channels.add(text)
                href = link.get('href', '')
                if href and ('.m3u' in href or 'playlist' in href.lower()):
                    all_urls.add(href)
            
            # 2. Buscar todos los patrones de países
            print("  - Buscando patrones de países...")
            countries = ['SP', 'UK', 'PT', 'DE', 'FR', 'IT', 'BE', 'PL', 'RO', 'AL', 'NO', 'FI', 'AT', 'RU', 'US', 'CA', 'MX', 'AR', 'CO', 'CL', 'BR', 'VE', 'PE', 'EC', 'GT', 'SV', 'HN', 'CR', 'PA', 'MT', 'IE', 'SLOVENIA', 'MONTENEGRO', 'AZE', 'RUS']
            
            for country in countries:
                # |XX| CANAL
                pattern1 = rf'\|{country}\|\s*([^\n<]+)'
                for m in re.findall(pattern1, html):
                    name = m.strip()[:50]
                    if name and len(name) > 2:
                        all_channels.add(name)
                
                # XX - CANAL
                pattern2 = rf'\b{country}\s*[-–—]\s*([A-Za-z0-9\s\-\.\+]+?)(?:\n|<|,)'
                for m in re.findall(pattern2, html, re.IGNORECASE):
                    name = m.strip()[:50]
                    if name and len(name) > 2:
                        all_channels.add(name)
            
            # 3. Buscar en scripts
            print("  - Buscando en scripts...")
            for script in soup.find_all('script'):
                if script.string:
                    js = script.string
                    # Arrays de strings
                    for m in re.findall(r'"([A-Z][A-Za-z0-9\s\-\.\+]{3,40})"', js):
                        if len(m) > 3:
                            all_channels.add(m)
                    # URLs M3U
                    for m in re.findall(r'"(https?://[^"]*\.m3u[^"]*)"', js):
                        all_urls.add(m)
            
            # 4. Buscar en todo el texto
            print("  - Buscando en texto...")
            text_content = soup.get_text()
            
            # Buscar nombres solos (sin país)
            for m in re.findall(r'\b([A-Z][A-Za-z\s]{3,25})\b', text_content):
                if len(m) > 4:
                    all_channels.add(m.strip())
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  ERROR: {e}")
    
    # Limpiar
    print(f"\n[LIMPIANDO] {len(all_channels)} candidatos...")
    
    nav_words = ['home', 'contact', 'setup', 'guide', 'whatsapp', 'subscribe', 'login', 'menu', 
                 'click', 'select', 'choose', 'loading', 'error', 'page', 'footer', 'header', 
                 'skip', 'channel', 'channels', 'list', 'section', 'euro', 'america', 'asia', 
                 'africa', 'australia', 'arabic', 'europe', 'world', 'premium', 'free', 'trial',
                 'hevc', 'fhd', 'hd', '4k', 'uhd']
    
    cleaned = []
    for ch in all_channels:
        ch = ch.strip()
        ch_lower = ch.lower()
        
        if len(ch) < 3 or len(ch) > 45:
            continue
        if not re.search(r'[a-zA-Z]', ch):
            continue
        
        skip = False
        for w in nav_words:
            if w in ch_lower:
                skip = True
                break
        if skip:
            continue
        
        cleaned.append(ch)
    
    unique = sorted(set(cleaned))
    print(f"[RESULTADO] {len(unique)} canales únicos")
    print(f"[URLs] {len(all_urls)} URLs encontradas")
    
    return unique, list(all_urls)

def add_channels_to_db(channel_list):
    conn = get_db_connection()
    cursor = conn.cursor()
    added = 0
    
    print(f"\n[INSERTANDO] {len(channel_list)} canales...")
    
    for name in channel_list:
        name = name.strip()
        if not name:
            continue
        
        # Categorizar
        name_lower = name.lower()
        if any(x in name_lower for x in ['sport', 'futbol', 'football', 'soccer', 'liga', 'champions', 'nba', 'nfl']):
            cat = 'Deportes'
        elif any(x in name_lower for x in ['movie', 'cine', 'cinema', 'film', 'hbo', 'amc', 'paramount', 'fox', 'action']):
            cat = 'Cine'
        elif any(x in name_lower for x in ['news', 'cnn', 'bbc', 'al jazeera', 'rt', 'sky news']):
            cat = 'Noticias'
        elif any(x in name_lower for x in ['kids', 'disney', 'cartoon', 'nick', 'boomerang', 'baby']):
            cat = 'Infantil'
        elif any(x in name_lower for x in ['music', 'mtv', 'vh1', 'trace']):
            cat = 'Musica'
        elif any(x in name_lower for x in ['discovery', 'nat geo', 'history', 'animal', 'science']):
            cat = 'Documental'
        else:
            cat = 'General'
        
        try:
            cursor.execute("INSERT OR IGNORE INTO channels (name, category, stream_count) VALUES (?, ?, 0)", (name, cat))
            if cursor.rowcount > 0:
                added += 1
        except:
            pass
    
    conn.commit()
    conn.close()
    print(f"[DB] Agregados: {added}")
    return added

def main():
    print("=" * 60)
    print("MAX IPTV 4K - EXTRACCION TOTAL v3")
    print("=" * 60)
    
    channels, urls = extract_everything()
    
    # Guardar JSON
    with open('maxiptv_all_channels.json', 'w') as f:
        json.dump({'channels': channels, 'm3u_urls': urls}, f, indent=2)
    print(f"\n[GUARDADO] maxiptv_all_channels.json")
    
    if channels:
        add_channels_to_db(channels)
    
    print("\nCOMPLETADO!")

if __name__ == '__main__':
    main()