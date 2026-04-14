import urllib, time

SEARCHTV = 'https://searchtv.net/'
_last_error = None

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': SEARCHTV,
}

def get_scraper():
    from curl_cffi import requests as cf_requests
    session = cf_requests.Session(impersonate='chrome124')
    try:
        session.get(SEARCHTV, timeout=10, headers=HEADERS)
    except:
        pass
    return session

def search(query, limit=20, offset=0):
    global _last_error
    result = {'streams': [], 'status': 'ok', 'results': 0, 'total': 0}
    
    try:
        scraper = get_scraper()
        resp = scraper.get(
            SEARCHTV + 'search/?query=' + urllib.parse.quote(query),
            timeout=10,
            headers=HEADERS
        )
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
                r = scraper.get(
                    SEARCHTV + 'stream/uuid/' + item_id + '/',
                    timeout=5,
                    headers=HEADERS
                )
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
    return {'scraper_ready': True, 'last_error': _last_error}