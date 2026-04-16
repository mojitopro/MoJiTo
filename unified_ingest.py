import json
import sqlite3
import os
from db_utils import get_db_path

def normalize_channel(name):
    name = name.lower().strip()
    name = name.replace(' -co', '').replace(' -mx', '').replace(' -ar', '').replace(' -cl', '').replace(' -ve', '')
    name = name.replace('  ', ' ')
    return name

def load_all_raw():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    total_streams = 0
    total_nodes = 0
    
    # Load playlist.json
    for path in ['../pirate/playlist.json', 'playlist.json']:
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
            
            channels = data.get('channels', [])
            for ch in channels:
                channel = normalize_channel(ch['name'])
                urls = ch.get('urls', [])
                
                for url in urls:
                    # Extract IP and port for nodes table
                    try:
                        if '://' in url:
                            rest = url.split('://')[1]
                            ip = rest.split(':')[0]
                            port = rest.split(':')[1].split('/')[0] if ':' in rest else '80'
                            
                            # Insert node if not exists
                            cursor.execute("""
                                INSERT OR IGNORE INTO nodes (ip, port, country, cluster)
                                VALUES (?, ?, 'UNKNOWN', ?)
                            """, (ip, port, ".".join(ip.split(".")[:2])))
                            total_nodes += 1
                    except:
                        pass
                    
                    # Insert stream
                    try:
                        cursor.execute("""
                            INSERT OR IGNORE INTO streams (url, channel, status)
                            VALUES (?, ?, 'pending')
                        """, (url, channel))
                        total_streams += 1
                    except:
                        pass
    
    # Load nodes.json directly
    for path in ['nodes.json', '../nodes.json']:
        if os.path.exists(path):
            with open(path) as f:
                nodes = json.load(f)
            
            for n in nodes:
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO nodes (ip, port, country, cluster)
                        VALUES (?, ?, 'UNKNOWN', ?)
                    """, (n['ip'], n['port'], ".".join(n['ip'].split(".")[:2])))
                except:
                    pass
    
    conn.commit()
    
    # Get actual counts
    cursor.execute("SELECT COUNT(*) FROM streams")
    streams_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM nodes")
    nodes_count = cursor.fetchone()[0]
    
    print(f"✔ Streams: {streams_count}")
    print(f"✔ Nodes: {nodes_count}")
    return streams_count, nodes_count

if __name__ == '__main__':
    load_all_raw()
