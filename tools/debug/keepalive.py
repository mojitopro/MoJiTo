import os
import time
import requests
import random

RENDER_URL = os.environ.get('RENDER_URL', 'https://mojitopro.onrender.com')
PING_INTERVAL = 25
MAX_RETRIES = 3

ENDPOINTS = [
    '/',
    '/api/status',
    '/tv',
    '/api/channels',
]

def ping_url(url, timeout=5):
    try:
        r = requests.get(url, timeout=timeout)
        return r.status_code == 200
    except:
        return False

def ping_loop():
    print(f'Keepalive iniciado -> {RENDER_URL}')
    consecutive_failures = 0
    
    while True:
        try:
            # Ping a random endpoint each time to avoid caching issues
            endpoint = random.choice(ENDPOINTS)
            url = RENDER_URL + endpoint
            
            success = ping_url(url, timeout=10)
            
            if success:
                consecutive_failures = 0
                print(f'✓ Ping {endpoint} OK')
            else:
                consecutive_failures += 1
                print(f'✗ Ping {endpoint} failed ({consecutive_failures})')
                
                # If multiple failures, try all endpoints
                if consecutive_failures >= 2:
                    print('Trying all endpoints...')
                    for ep in ENDPOINTS:
                        ping_url(RENDER_URL + ep, timeout=5)
                    
            # Add some randomness to avoid detection as bot
            time.sleep(PING_INTERVAL + random.randint(0, 10))
            
        except Exception as e:
            consecutive_failures += 1
            print(f'Error: {e}')
            time.sleep(PING_INTERVAL)

if __name__ == '__main__':
    print('Iniciando keepalive robusto...')
    print(f'URL: {RENDER_URL}')
    print(f'Pings cada {PING_INTERVAL}s')
    ping_loop()