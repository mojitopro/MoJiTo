#!/usr/bin/env python3
"""
Add ANY channel - searches searchtv.net
Usage: python tools/add_channel.py "Any Channel Name"
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scraper import searchtv

CHANNELS_FILE = Path(__file__).parent.parent / 'custom_channels.json'


def load_channels():
    if CHANNELS_FILE.exists():
        with open(CHANNELS_FILE) as f:
            return json.load(f)
    return []


def save_channels(channels):
    with open(CHANNELS_FILE, 'w') as f:
        json.dump(channels, f, indent=2)


def find_existing(channels, name):
    name_lower = name.lower()
    for i, ch in enumerate(channels):
        if ch.get('name', '').lower() == name_lower:
            return i, ch
    return None, None


def list_channels():
    channels = load_channels()
    if not channels:
        print("No channels saved")
        return
    print(f"Saved channels ({len(channels)}):")
    for ch in channels:
        backups = ch.get('backups', [])
        print(f"  - {ch['name']}: {len(backups)} urls")


def remove_channel(name):
    channels = load_channels()
    idx, existing = find_existing(channels, name)
    if idx is None:
        print(f"Channel '{name}' not found")
        return False
    del channels[idx]
    save_channels(channels)
    print(f"Removed: {existing['name']}")
    return True


def clear_all():
    save_channels([])
    print("Cleared all channels")


def add_channel(channel_name):
    print(f"Searching: {channel_name}...")

    result = searchtv.search(channel_name, limit=100)

    if result['status'] != 'ok':
        print(f"Error: {result.get('error', result['status'])}")
        sys.exit(1)

    streams = result.get('streams', [])
    if not streams:
        print("No streams found. Try another name.")
        sys.exit(1)

    urls = [s['url'] for s in streams]
    print(f"Found {len(urls)} streams")

    channels = load_channels()
    idx, existing = find_existing(channels, channel_name)

    if existing:
        print(f"Channel '{existing['name']}' already exists, updating...")
        existing['url'] = urls[0]
        existing['backups'] = urls
    else:
        channels.append({
            "name": channel_name,
            "url": urls[0],
            "backups": urls
        })
        print(f"Added: {channel_name}")

    save_channels(channels)
    print(f"Saved to custom_channels.json")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python tools/add_channel.py \"Channel Name\"   - Add any channel")
        print("  python tools/add_channel.py --remove \"Name\"  - Remove channel")
        print("  python tools/add_channel.py --list        - List channels")
        print("  python tools/add_channel.py --clear       - Clear all")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == '--list':
        list_channels()
    elif cmd == '--clear':
        clear_all()
    elif cmd == '--remove':
        if len(sys.argv) < 3:
            print("Usage: python tools/add_channel.py --remove \"Channel Name\"")
            sys.exit(1)
        remove_channel(sys.argv[2])
    else:
        add_channel(cmd)


if __name__ == '__main__':
    main()