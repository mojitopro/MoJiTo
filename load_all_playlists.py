import json
import sqlite3
import os

def load_playlists():
    db_path = os.environ.get('DB_PATH', 'streams.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    total = 0
    
    # Load pirate/playlist.json
    pirate_path = '../pirate/playlist.json'
    if os.path.exists(pirate_path):
        with open(pirate_path) as f:
            data = json.load(f)
        
        for ch in data.get('channels', []):
            channel = ch.get('name', 'unknown')
            urls = ch.get('urls', [])
            for url in urls:
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO streams (url, channel, status)
                        VALUES (?, ?, 'unknown')
                    """, (url, channel))
                    total += 1
                except:
                    pass
    
    # Load sofagent/sof-playlist.json
    sof_path = '../sofagent/sof-playlist.json'
    if os.path.exists(sof_path):
        with open(sof_path) as f:
            data = json.load(f)
        
        for ch in data.get('channels', []):
            channel = ch.get('name', 'unknown')
            url = ch.get('url', '')
            if url:
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO streams (url, channel, status)
                        VALUES (?, ?, 'unknown')
                    """, (url, channel))
                    total += 1
                except:
                    pass
    
    conn.commit()
    
    # Get total
    cursor.execute("SELECT COUNT(*) FROM streams")
    streams_total = cursor.fetchone()[0]
    
    print(f"Total insertados: {streams_total}")
    return streams_total

if __name__ == '__main__':
    load_playlists()