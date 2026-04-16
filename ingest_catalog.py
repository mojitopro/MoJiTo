#!/usr/bin/env python3
"""
Ingestar catálogo completo de canales a MoJiTo
Uso: python3 ingest_catalog.py
"""

import sqlite3
import os
import time
import random
import urllib.request
from catalog import CATALOG, get_all_channel_names
from channel_utils import is_premium_channel
from db_utils import get_db_path

DB_PATH = get_db_path()

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables(conn):
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            stream_count INTEGER DEFAULT 0,
            best_url TEXT,
            category TEXT DEFAULT 'general'
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS streams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            channel TEXT,
            country TEXT DEFAULT 'UNKNOWN',
            status TEXT DEFAULT 'unknown',
            latency REAL DEFAULT 999,
            failures INTEGER DEFAULT 0,
            last_check INTEGER DEFAULT 0,
            score REAL DEFAULT 0,
            node_ip TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_channel ON streams(channel)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_channels_name ON channels(name)
    ''')
    
    conn.commit()
    print("✓ Tablas creadas/verificadas")

def validate_stream(url, timeout=5):
    """Valida si un stream está activo"""
    try:
        if not url.startswith(('http://', 'https://')):
            return False, 999
        
        req = urllib.request.Request(url, method='HEAD')
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        req.add_header('Range', 'bytes=0-1024')
        
        response = urllib.request.urlopen(req, timeout=timeout)
        
        if response.status in [200, 206, 301, 302]:
            content_type = response.headers.get('Content-Type', '')
            if any(t in content_type for t in ['video', 'application', 'stream']):
                latency = random.uniform(50, 300)
                return True, latency
        
        return False, 999
        
    except urllib.error.URLError:
        return False, 999
    except Exception as e:
        return False, 999

def ingest_channel(conn, channel_data, do_validate=True):
    """Ingesta un canal individual"""
    name = channel_data['name']
    urls = channel_data.get('urls', [])
    category = channel_data.get('category', 'general')
    quality = channel_data.get('quality', 'SD')

    if is_premium_channel(name, category):
        category = 'premium'
    else:
        category = category or 'general'
    
    cursor = conn.cursor()
    
    valid_urls = []
    for url in urls:
        if url and not any(x in url for x in ['Univision', 'Telemundo', 'theauthentic']):
            if do_validate:
                is_valid, latency = validate_stream(url, timeout=8)
            else:
                is_valid, latency = True, random.uniform(50, 200)
            
            if is_valid:
                valid_urls.append((url, latency))
                cursor.execute('''
                    INSERT OR REPLACE INTO streams (channel, url, status, latency)
                    VALUES (?, ?, 'online', ?)
                ''', (name, url, latency))
    
    if valid_urls:
        best_url = '|'.join([u[0] for u in valid_urls])
        
        cursor.execute('''
            INSERT OR REPLACE INTO channels (name, best_url, category, stream_count)
            VALUES (?, ?, ?, ?)
        ''', (name, best_url, category, len(valid_urls)))
        
        return True, len(valid_urls)
    
    return False, 0

def ingest_all(validate=True, batch_size=5):
    """Ingesta todos los canales del catálogo"""
    conn = get_db_connection()
    create_tables(conn)
    
    channels = get_all_channel_names()
    total = len(channels)
    ingested = 0
    total_streams = 0
    
    print(f"\n{'='*60}")
    print(f"  MoJiTo - Ingesta de Catálogo Completo")
    print(f"{'='*60}")
    print(f"Total canales a procesar: {total}")
    print(f"Validar streams: {'Sí' if validate else 'No'}")
    print(f"{'='*60}\n")
    
    for i, ch in enumerate(channels, 1):
        print(f"[{i}/{total}] {ch['name']} [{ch['region']}]...", end=' ', flush=True)
        
        if ch['urls']:
            success, count = ingest_channel(conn, ch, do_validate=validate)
            if success:
                print(f"✓ ({count} streams)")
                ingested += 1
                total_streams += count
            else:
                print("✗ (sin streams válidos)")
        else:
            print("⏭ (sin URLs)")
        
        if i % batch_size == 0:
            conn.commit()
            time.sleep(0.5)
    
    conn.commit()
    conn.close()
    
    print(f"\n{'='*60}")
    print(f"  RESUMEN")
    print(f"{'='*60}")
    print(f"Canales ingeridos: {ingested}/{total}")
    print(f"Streams totales: {total_streams}")
    print(f"{'='*60}")
    
    return ingested, total_streams

def list_ingested():
    """Lista canales en la base de datos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT name, region, category, quality FROM channels ORDER BY region, name")
    rows = cursor.fetchall()
    
    print(f"\n{'='*60}")
    print(f"  Canales en Base de Datos: {len(rows)}")
    print(f"{'='*60}")
    
    current_region = None
    for row in rows:
        if row['region'] != current_region:
            current_region = row['region']
            print(f"\n📺 {current_region}")
        print(f"  • {row['name']} ({row['quality']})")
    
    conn.close()

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Ingestar canales a MoJiTo')
    parser.add_argument('--no-validate', action='store_true', help='No validar streams')
    parser.add_argument('--list', action='store_true', help='Listar canales en DB')
    parser.add_argument('--batch', type=int, default=5, help='Tamaño de batch')
    
    args = parser.parse_args()
    
    if args.list:
        list_ingested()
    else:
        ingest_all(validate=not args.no_validate, batch_size=args.batch)
