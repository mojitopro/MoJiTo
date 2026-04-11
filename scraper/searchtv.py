import urllib.parse
import time
import traceback

SEARCHTV = "https://searchtv.net/"

_scraper = None
_last_error = None
_last_scrape_time = None

def init_scraper():
    global _scraper
    try:
        import cloudscraper
        _scraper = cloudscraper.create_scraper()
        _scraper.get(SEARCHTV, timeout=10)
    except Exception as e:
        _scraper = None
    return _scraper

def get_scraper():
    global _scraper
    if _scraper is None:
        return init_scraper()
    return _scraper

def search(query, limit=20):
    global _last_error, _last_scrape_time
    
    scraper = get_scraper()
    result = {
        'streams': [],
        'status': 'ok',
        'source': 'live',
        'cached': False,
        'results': 0
    }
    
    if scraper is None:
        _last_error = 'scraper not available'
        result['status'] = 'error'
        result['error'] = _last_error
        return result
    
    start_time = time.time()
    
    try:
        resp = scraper.get(f"{SEARCHTV}search/?query={urllib.parse.quote(query)}", timeout=10)
        
        if resp.status_code != 200:
            _last_error = f"HTTP {resp.status_code}"
            result['status'] = 'blocked'
            result['error'] = _last_error
            return result
        
        items = resp.json()
        result['results'] = len(items)
        _last_scrape_time = time.time() - start_time
        
        streams = []
        for item_id, info in list(items.items())[:limit]:
            try:
                r = scraper.get(f"{SEARCHTV}stream/uuid/{item_id}/", timeout=3)
                if 'EXTM3U' in r.text:
                    for line in r.text.strip().split('\n'):
                        if line.startswith('http'):
                            streams.append({
                                'url': line.strip(),
                                'title': info.get('title', item_id)
                            })
                            break
            except:
                pass
        
        streams.sort(key=lambda x: 1 if '1080' in x['title'].lower() or 'hd' in x['title'].lower() else 2)
        result['streams'] = streams
        result['results'] = len(streams)
        
    except Exception as e:
        _last_error = str(e)[:50]
        _last_trace = traceback.format_exc()[:100]
        result['status'] = 'error'
        result['error'] = _last_error
        result['trace'] = _last_trace
        result['duration'] = time.time() - start_time
    
    return result

def get_status():
    return {
        'scraper_ready': _scraper is not None,
        'last_error': _last_error,
        'last_scrape_time': _last_scrape_time
    }