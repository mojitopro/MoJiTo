import urllib, time

SEARCHTV = "https://searchtv.net/"
_scraper = None
_last_error = None

def get_scraper():
    global _scraper
    if _scraper is None:
        try:
            import cloudscraper
            _scraper = cloudscraper.create_scraper()
            _scraper.get(SEARCHTV, timeout=10)
        except:
            _scraper = False
    return _scraper if _scraper else None

def search(query, limit=20, offset=0):
    global _last_error
    scraper = get_scraper()
    result = {'streams': [], 'status': 'ok', 'results': 0, 'total': 0}
    
    if not scraper:
        result['status'] = 'error'
        result['error'] = 'scraper unavailable'
        return result
    
    try:
        resp = scraper.get(SEARCHTV + "search/?query=" + urllib.parse.quote(query), timeout=10)
        if resp.status_code != 200:
            result['status'] = 'blocked'
            result['error'] = 'HTTP ' + str(resp.status_code)
            return result
        
        items = resp.json()
        result['total'] = len(items)
        
        all_items = list(items.items())
        paginated = all_items[offset:offset+limit]
        
        streams = []
        for item_id, info in paginated:
            try:
                r = scraper.get(SEARCHTV + "stream/uuid/" + item_id + "/", timeout=3)
                if 'EXTM3U' in r.text:
                    for line in r.text.strip().split('\n'):
                        if line.startswith('http'):
                            streams.append({'url': line.strip(), 'title': info.get('title', item_id)})
                            break
            except:
                pass
        
        streams.sort(key=lambda x: 1 if '1080' in x['title'].lower() or 'hd' in x['title'].lower() else 2)
        result['streams'] = streams
        result['results'] = len(streams)
        result['offset'] = offset
        result['limit'] = limit
        
    except Exception as e:
        _last_error = str(e)[:50]
        result['status'] = 'error'
        result['error'] = _last_error
    
    return result

def get_status():
    return {'scraper_ready': bool(_scraper), 'last_error': _last_error}