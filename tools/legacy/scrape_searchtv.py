import requests
import time
import json

SEARCHTV = "https://searchtv.net/"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

def scrape_channel(channel_name):
    """Scrape all streams for a channel"""
    try:
        url = SEARCHTV + "search/?query=" + requests.utils.quote(channel_name)
        resp = requests.get(url, headers=HEADERS, timeout=10)
        
        if resp.status_code != 200:
            print(f"  Error HTTP {resp.status_code}")
            return []
        
        data = resp.json()
        return data
    except Exception as e:
        print(f"  Error: {e}")
        return []

def scrape_all():
    queries = [
        'espn', 'hbo', 'fox', 'nickelodeon', 'discovery', 
        'nat geo', 'history', 'cnn', 'tnt', 'amc',
        'adult swim', 'cartoon', 'anime', 'movie', 'music',
        'univision', 'telemundo', 'starz', 'showtime', 'cinemax'
    ]
    
    all_channels = {}
    
    for q in queries:
        print(f"Buscando: {q}")
        data = scrape_channel(q)
        
        if data:
            all_channels.update(data)
            print(f"  -> {len(data)} canales")
        
        time.sleep(1)  # Rate limit
    
    # Save
    with open('scraped_channels.json', 'w') as f:
        json.dump(all_channels, f)
    
    print(f"\nTotal: {len(all_channels)} canales")
    return all_channels

if __name__ == '__main__':
    scrape_all()