import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from db import get_connection

def check_stream(url):
    try:
        start = time.time()
        r = requests.head(url, timeout=3, allow_redirects=True)
        latency = time.time() - start
        
        if r.status_code == 200:
            return (url, 'online', latency, 0)
        elif r.status_code == 404:
            return (url, 'not_found', 999, 1)
        else:
            return (url, 'offline', 999, 1)
    except requests.exceptions.Timeout:
        return (url, 'timeout', 999, 1)
    except:
        return (url, 'error', 999, 1)

def validate_batch(batch_size=100, workers=30):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get pending streams
    cursor.execute("SELECT id, url FROM streams WHERE status='unknown' LIMIT ?", (batch_size,))
    streams = cursor.fetchall()
    
    if not streams:
        cursor.execute("SELECT id, url FROM streams WHERE status='offline' AND last_check < ? LIMIT ?", 
                      (int(time.time()) - 3600, batch_size))
        streams = cursor.fetchall()
    
    print(f"Validando {len(streams)} streams...")
    
    results = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(check_stream, s['url']): s for s in streams}
        for future in as_completed(futures):
            results.append(future.result())
    
    # Update DB
    for url, status, latency, failures in results:
        cursor.execute("""
            UPDATE streams 
            SET status=?, latency=?, last_check=?, failures=failures+?
            WHERE url=?
        """, (status, latency, int(time.time()), failures, url))
    
    conn.commit()
    
    online = sum(1 for r in results if r[1] == 'online')
    print(f"✓ {online}/{len(streams)} online")
    return len(results)

def validate_all(limit=1000, workers=50):
    total = 0
    while True:
        count = validate_batch(limit - total, workers)
        total += count
        if count < 50 or total >= limit:
            break
    print(f"Validación completa: {total} streams procesados")

if __name__ == '__main__':
    validate_all(200, 30)