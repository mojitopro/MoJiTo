import sqlite3
import os

def get_all_channels():
    db_path = os.environ.get('DB_PATH', 'streams.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM channels ORDER BY name")
    return [r[0] for r in cursor.fetchall()]

def get_best_stream(channel):
    db_path = os.environ.get('DB_PATH', 'streams.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Try exact match first
    cursor.execute("SELECT best_url FROM channels WHERE LOWER(name)=?", (channel.lower(),))
    result = cursor.fetchone()
    
    if result and result[0]:
        url = result[0]
        # Handle multiple URLs (pipe separated for fallback)
        if '|' in url:
            urls = url.split('|')
            return {'url': urls[0], 'fallbacks': urls[1:], 'channel': channel}
        return {'url': url, 'fallbacks': [], 'channel': channel}
    
    # Try partial match
    cursor.execute("SELECT name, best_url FROM channels WHERE LOWER(name) LIKE ?", 
                  (f'%{channel.lower()}%',))
    result = cursor.fetchone()
    
    if result:
        url = result[1]
        if '|' in url:
            urls = url.split('|')
            return {'url': urls[0], 'fallbacks': urls[1:], 'channel': result[0]}
        return {'url': url, 'fallbacks': [], 'channel': result[0]}
    
    # Search in streams directly
    cursor.execute("""
        SELECT url, latency FROM streams 
        WHERE LOWER(channel) LIKE ? AND status='online'
        ORDER BY latency LIMIT 1
    """, (f'%{channel.lower()}%',))
    result = cursor.fetchone()
    
    if result:
        return {'url': result[0], 'fallbacks': [], 'channel': channel, 'source': 'direct'}
    
    return None

if __name__ == '__main__':
    print(get_all_channels())