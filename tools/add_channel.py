#!/usr/bin/env python3.13
"""
Add channel to custom_channels.json
Usage: python tools/add_channel.py "Channel Name"
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
    for ch in channels:
        if ch.get('name', '').lower() == name_lower:
            return ch
    return None


def main():
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} \"Channel Name\"")
        print("Example: python tools/add_channel.py \"Adult Swim\"")
        sys.exit(1)

    channel_name = sys.argv[1]
    print(f"Searching for: {channel_name}...")

    result = searchtv.search(channel_name, limit=15)

    if result['status'] != 'ok':
        print(f"Error: {result.get('error', result['status'])}")
        sys.exit(1)

    streams = result.get('streams', [])
    print(f"Found {len(streams)} streams")

    if not streams:
        print("No streams found")
        sys.exit(1)

    channels = load_channels()
    existing = find_existing(channels, channel_name)

    if existing:
        print(f"Channel '{existing['name']}' already exists")
        primary = existing['url']
        existing_backups = set(existing.get('backups', []))

        added_backups = []
        for stream in streams:
            url = stream['url']
            if url != primary and url not in existing_backups:
                existing_backups.add(url)
                added_backups.append(url)
                print(f"  Added backup: {url}")

        existing['backups'] = list(existing_backups)

        if added_backups:
            print(f"Added {len(added_backups)} new backups")
            save_channels(channels)
            print("Updated custom_channels.json")
        else:
            print("No new backups to add")
    else:
        primary = streams[0]['url']
        backups = [s['url'] for s in streams[:6]]

        new_channel = {
            "name": channel_name,
            "url": primary,
            "backups": backups
        }
        channels.append(new_channel)

        print(f"Added new channel: {channel_name}")
        print(f"  Primary: {primary}")
        print(f"  Backups: {len(backups) - 1}")

        save_channels(channels)
        print("Saved to custom_channels.json")


if __name__ == '__main__':
    main()