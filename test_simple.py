#!/usr/bin/env python3
"""
Simple Stream Tester - HTTP HEAD only
"""
import json
import requests
import socket

socket.setdefaulttimeout(3)

HEADERS = {'User-Agent': 'Mozilla/5.0'}

def test(url):
    try:
        r = requests.head(url, timeout=3, headers=HEADERS)
        return r.status_code, r.headers.get('Server', '')[:20]
    except Exception as e:
        return 0, str(e)[:20]

def main():
    with open('premium_consolidated.json') as f:
        data = json.load(f)
    
    working = []
    
    for ch in data['channels']:
        name = ch['name']
        all_urls = [ch.get('url', '')] + ch.get('fallbacks', [])
        
        code, server = 0, ''
        for u in all_urls:
            if u:
                code, server = test(u)
                if code == 200:
                    break
        
        if code == 200:
            working.append({'name': name, 'server': server, 'url': all_urls[0]})
            print(f"OK: {name}")
        else:
            print(f"FAIL: {name} - HTTP {code}")
    
    with open('working_streams.json', 'w') as f:
        json.dump(working, f, indent=2)
    
    print(f"\nWorking: {len(working)}/{len(data['channels'])}")

if __name__ == '__main__':
    main()