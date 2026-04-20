import urllib, time
import httpx
import concurrent.futures

SEARCHTV = 'https://searchtv.net/'
_last_error = None

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': '*/*',
}

_scraper = None


def get_scraper():
    global _scraper
    if _scraper is None:
        _scraper = httpx.Client(
            headers=HEADERS,
            timeout=30.0,
            follow_redirects=True
        )
    return _scraper


def fetch_stream(item_id, info):
    try:
        r = get_scraper().get(
            SEARCHTV + 'stream/uuid/' + item_id + '/',
            timeout=8
        )
        if 'EXTM3U' in r.text:
            for line in r.text.strip().split('\n'):
                if line.startswith('http'):
                    return {'url': line.strip(), 'title': info.get('title', item_id)}
    except:
        pass
    return None


def search(query, limit=50, offset=0):
    global _last_error
    result = {'streams': [], 'status': 'ok', 'results': 0, 'total': 0}

    try:
        scraper = get_scraper()
        resp = scraper.get(
            SEARCHTV + 'search/?query=' + urllib.parse.quote(query),
            timeout=20
        )
        if resp.status_code != 200:
            result['status'] = 'blocked'
            result['error'] = 'HTTP ' + str(resp.status_code)
            return result

        items = resp.json()
        result['total'] = len(items)

        all_items = list(items.items())
        paginated = all_items[offset:offset + limit]

        streams = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(fetch_stream, item_id, info): item_id
                      for item_id, info in paginated}
            for f in concurrent.futures.as_completed(futures, timeout=30):
                try:
                    s = f.result()
                    if s:
                        streams.append(s)
                except:
                    pass

        result['streams'] = streams
        result['results'] = len(streams)

    except Exception as e:
        _last_error = str(e)[:50]
        result['status'] = 'error'
        result['error'] = _last_error

    return result


def get_status():
    return {'scraper_ready': True, 'last_error': _last_error}