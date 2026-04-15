#!/usr/bin/env python3
"""Limpiar y reorganizar canales en la DB"""
import sqlite3
import os

DB_PATH = os.environ.get('DB_PATH', 'streams.db')

def clean_channels():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Obtener todos los canales
    cursor.execute("SELECT name, best_url, category FROM channels")
    channels = cursor.fetchall()
    
    print(f"Canales totales en DB: {len(channels)}")
    
    # Limpiar nombres problemáticos
    cleaned = []
    for name, url, cat in channels:
        # Saltar canales con nombres muy extraños
        if name.startswith('&') or name.startswith('*') or name.startswith(')'):
            continue
        if len(name) < 2:
            continue
        cleaned.append((name, url, cat or 'general'))
    
    # Recrear tabla limpia
    cursor.execute("DROP TABLE IF EXISTS channels")
    cursor.execute('''
        CREATE TABLE channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            stream_count INTEGER DEFAULT 0,
            best_url TEXT,
            category TEXT DEFAULT 'general'
        )
    ''')
    
    for name, url, cat in cleaned:
        cursor.execute('''
            INSERT OR IGNORE INTO channels (name, best_url, category)
            VALUES (?, ?, ?)
        ''', (name, url, cat))
    
    conn.commit()
    
    # Verificar
    cursor.execute("SELECT COUNT(*) FROM channels")
    count = cursor.fetchone()[0]
    print(f"Canales limpios: {count}")
    
    # Mostrar muestra
    cursor.execute("SELECT name FROM channels ORDER BY name LIMIT 30")
    print("\nPrimeros 30 canales:")
    for row in cursor.fetchall():
        print(f"  - {row[0]}")
    
    conn.close()

if __name__ == '__main__':
    clean_channels()
