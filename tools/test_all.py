#!/usr/bin/env python3
"""
Test all streams for a channel - fast parallel testing
Usage: python tools/test_all.py "Channel Name"
"""
import json
import sys
import asyncio
import aiohttp
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scraper import searchtv

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': '*/*',
}


async def test_url(session, url):
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=5), headers=HEADERS) as r:
            if r.status in (200, 301, 302, 303, 308):
                text = await r.text()
                if 'EXTM3U' in text or '#EXTM3U' in text:
                    return url, 'ok'
                return url, 'no-m3u8'
            return url, f'http-{r.status}'
    except asyncio.TimeoutError:
        return url, 'timeout'
    except Exception as e:
        return url, f'error-{str(e)[:20]}'


async def test_all(urls):
    connector = aiohttp.TCPConnector(limit=50)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [test_url(session, u) for u in urls]
        results = await asyncio.gather(*tasks)
    return results


def main():
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} \"Channel Name\"")
        sys.exit(1)

    channel_name = sys.argv[1]
    print(f"Searching: {channel_name}...")

    result = searchtv.search(channel_name, limit=100)
    if result['status'] != 'ok':
        print(f"Error: {result.get('error', result['status'])}")
        sys.exit(1)

    streams = result.get('streams', [])
    urls = [s['url'] for s in streams]
    print(f"Found {len(urls)} URLs, testing...")

    if not urls:
        print("No streams found")
        sys.exit(1)

    results = asyncio.run(test_all(urls))

    working = []
    failed = []
    for url, status in results:
        if status == 'ok':
            working.append(url)
        else:
            failed.append((url, status))

    print(f"\n=== {channel_name} ===")
    print(f"Working: {len(working)}/{len(urls)}")
    print(f"\n--- WORKING ({len(working)}) ---")
    for url in working:
        print(url)

    if failed:
        print(f"\n--- FAILED ({len(failed)}) ---")
        for url, status in failed[:10]:
            print(f"{status}: {url[:60]}")

    save = input(f"\nSave {len(working)} to custom_channels.json? (y/n): ")
    if save.lower() == 'y':
        CHANNELS_FILE = Path(__file__).parent.parent / 'custom_channels.json'
        channels = []
        if CHANNELS_FILE.exists():
            with open(CHANNELS_FILE) as f:
                channels = json.load(f)

        for ch in channels:
            if ch.get('name', '').lower() == channel_name.lower():
                existing = ch
                break
        else:
            existing = None

        if existing:
            existing['backups'] = working
        else:
            channels.append({
                "name": channel_name,
                "url": working[0] if working else "",
                "backups": working
            })

        with open(CHANNELS_FILE, 'w') as f:
            json.dump(channels, f, indent=2)
        print("Saved!")


if __name__ == '__main__':
    main()