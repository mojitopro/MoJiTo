import sqlite3
import os

def get_best_stream(channel):
    db_path = os.environ.get('DB_PATH', 'streams.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    channel = channel.lower().strip()
    
    cursor.execute("""
        SELECT url, latency, score 
        FROM streams
        WHERE channel LIKE ? AND status='online'
        ORDER BY score ASC
        LIMIT 1
    """, (f'%{channel}%',))
    
    result = cursor.fetchone()
    
    if result:
        return {
            'url': result['url'],
            'latency': result['latency'],
            'score': result['score']
        }
    
    cursor.execute("""
        SELECT url, latency, score 
        FROM streams
        WHERE channel LIKE ? 
        ORDER BY score ASC
        LIMIT 1
    """, (f'%{channel}%',))
    
    result = cursor.fetchone()
    
    if result:
        return {
            'url': result['url'],
            'latency': result['latency'],
            'score': result['score'],
            'offline': True
        }
    
    return None

def get_all_channels():
    db_path = os.environ.get('DB_PATH', 'streams.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT DISTINCT channel FROM streams ORDER BY channel")
    return [r[0] for r in cursor.fetchall()]

if __name__ == '__main__':
    print(get_best_stream('espn'))