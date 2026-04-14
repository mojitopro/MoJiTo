import time
import os
from db import get_connection
from validator import check_stream

def calculate_score(latency, failures):
    return latency + (failures * 10)

def update_scores():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, latency, failures FROM streams")
    streams = cursor.fetchall()
    
    for s in streams:
        score = calculate_score(s['latency'], s['failures'])
        cursor.execute("UPDATE streams SET score=? WHERE id=?", (score, s['id']))
    
    conn.commit()

def run():
    print('Iniciando scheduler...')
    
    while True:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, url FROM streams WHERE status='unknown' OR last_check < ? LIMIT 50", (int(time.time()) - 300,))
        streams = cursor.fetchall()
        
        if not streams:
            print('No hay streams pendientes')
            time.sleep(60)
            continue
        
        print(f'Checkeando {len(streams)} streams...')
        
        for s in streams:
            status = check_stream(s['id'], s['url'])
        
        update_scores()
        print('Ciclo completo')
        time.sleep(30)

if __name__ == '__main__':
    run()