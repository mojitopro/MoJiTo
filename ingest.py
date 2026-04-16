import json
import sqlite3
import os
from db_utils import get_db_path

def normalize_channel(name):
    name = name.lower().strip()
    name = name.replace(' -co', '').replace(' -mx', '').replace(' -ar', '').replace(' -cl', '')
    name = name.replace('  ', ' ')
    return name

def ingest_playlist(json_path='../pirate/playlist.json'):
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    if not os.path.exists(json_path):
        print(f'Archivo no encontrado: {json_path}')
        return
    
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    channels = data.get('channels', [])
    total = 0
    
    for ch in channels:
        channel = normalize_channel(ch['name'])
        urls = ch.get('urls', [])
        
        for url in urls:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO streams (url, channel, country, status)
                    VALUES (?, ?, 'UNKNOWN', 'unknown')
                """, (url, channel))
                total += 1
            except:
                pass
    
    conn.commit()
    print(f'Insertados {total} streams de {len(channels)} canales')

if __name__ == '__main__':
    ingest_playlist()
