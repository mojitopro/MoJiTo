import requests
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

SEARCHTV = "https://searchtv.net/"

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120',
})

def get_stream(channel_id):
    try:
        url = f"{SEARCHTV}stream/uuid/{channel_id}/"
        resp = session.get(url, timeout=5)
        if resp.status_code == 200 and '#EXTM3U' in resp.text:
            for line in resp.text.split('\n'):
                if line.startswith('http'):
                    return line.strip()
    except:
        pass
    return None

def extract_all_streams():
    # Load scraped channel IDs
    with open('scraped_channels.json') as f:
        data = json.load(f)
    
    channel_ids = list(data.keys())
    print(f"Extrayendo streams de {len(channel_ids)} canales...")
    
    streams = []
    results = {}
    
    # Process in batches with threads
    batch_size = 100
    for i in range(0, len(channel_ids), batch_size):
        batch = channel_ids[i:i+batch_size]
        print(f"Procesando {i}-{i+len(batch)}...")
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(get_stream, cid): cid for cid in batch}
            
            for future in as_completed(futures):
                cid = futures[future]
                try:
                    stream_url = future.result()
                    if stream_url:
                        title = data[cid].get('title', cid)
                        results[cid] = {'url': stream_url, 'title': title}
                except:
                    pass
        
        time.sleep(0.5)  # Rate limit between batches
    
    # Save results
    with open('extracted_streams.json', 'w') as f:
        json.dump(results, f)
    
    print(f"\nTotal streams extraídos: {len(results)}")
    
    # Group by channel name
    channels = {}
    for cid, info in results.items():
        title = info['title']
        # Extract channel name (before ' -')
        name = title.split(' -')[0].strip() if ' -' in title else title
        if name not in channels:
            channels[name] = []
        channels[name].append(info['url'])
    
    print(f"Canales únicos: {len(channels)}")
    
    # Save in format for DB
    with open('all_channels_for_db.json', 'w') as f:
        json.dump(channels, f)
    
    return results

if __name__ == '__main__':
    extract_all_streams()