import os
import time
import requests

RENDER_URL = os.environ.get('RENDER_URL', 'https://mojitopro.onrender.com')
PING_INTERVAL = 30

def ping_loop():
    while True:
        try:
            requests.get(RENDER_URL + '/api/status', timeout=10)
            print(f'Ping OK')
        except Exception as e:
            print(f'Ping failed: {e}')
        time.sleep(PING_INTERVAL)

if __name__ == '__main__':
    print('Worker iniciado - keepalive para Render')
    ping_loop()