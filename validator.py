import requests
import time
import sqlite3
import os
from db import get_connection

def check_stream(stream_id, url):
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        start = time.time()
        r = requests.head(url, timeout=5, allow_redirects=True)
        latency = time.time() - start
        
        if r.status_code == 200:
            status = 'online'
        else:
            status = 'offline'
    except Exception as e:
        status = 'offline'
        latency = 999
    
    cursor.execute("""
        UPDATE streams 
        SET status=?, latency=?, last_check=?
        WHERE id=?
    """, (status, latency, int(time.time()), stream_id))
    
    conn.commit()
    return status

def validate_all(limit=50):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, url FROM streams WHERE status='unknown' LIMIT ?", (limit,))
    streams = cursor.fetchall()
    
    print(f'Validando {len(streams)} streams...')
    
    for s in streams:
        status = check_stream(s['id'], s['url'])
        print(f"  {s['id']}: {status}")
    
    print('Validación completa')

if __name__ == '__main__':
    validate_all(20)