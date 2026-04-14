import json
import sqlite3
import os

def cluster_from_ip(ip):
    return ".".join(ip.split(".")[:2])

def ingest_nodes(json_path='nodes.json'):
    db_path = os.environ.get('DB_PATH', 'streams.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    if not os.path.exists(json_path):
        print(f'Archivo no encontrado: {json_path}')
        return
    
    with open(json_path) as f:
        nodes = json.load(f)

    for n in nodes:
        cluster = cluster_from_ip(n["ip"])
        cursor.execute("""
            INSERT OR IGNORE INTO nodes (ip, port, country, isp, cluster)
            VALUES (?, ?, ?, ?, ?)
        """, (n["ip"], n["port"], "UNKNOWN", "UNKNOWN", cluster))

    conn.commit()
    print(f"✔ {len(nodes)} nodos cargados")

if __name__ == "__main__":
    ingest_nodes()