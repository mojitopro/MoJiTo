#!/usr/bin/env python3
"""
Add channel to custom_channels.json
Usage:
  python tools/add_channel.py "Channel Name"    - Add/search channel
  python tools/add_channel.py --remove "Name"    - Remove channel and all backups
  python tools/add_channel.py --clear          - Clear all channels
  python tools/add_channel.py --list           - List all channels
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
        print(f"  - {ch['name']}: {len(backups)} backups")


def remove_channel(name):
    channels = load_channels()
    idx, existing = find_existing(channels, name)
    if idx is None:
        print(f"Channel '{name}' not found")
        return False
    del channels[idx]
    save_channels(channels)
    print(f"Removed channel: {existing['name']} ({len(existing.get('backups', []))} backups)")
    return True


def clear_all():
    channels = load_channels()
    if not channels:
        print("No channels to clear")
        return
    save_channels([])
    print(f"Cleared {len(channels)} channels")


def add_channel(channel_name):
    print(f"Searching for: {channel_name}...")

    result = searchtv.search(channel_name, limit=100)

    if result['status'] != 'ok':
        print(f"Error: {result.get('error', result['status'])}")
        sys.exit(1)

    streams = result.get('streams', [])
    print(f"Found {len(streams)} streams")

    if not streams:
        print("No streams found")
        sys.exit(1)

    channels = load_channels()
    idx, existing = find_existing(channels, channel_name)

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
        backups = [s['url'] for s in streams]

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


def main():
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} \"Channel Name\"")
        print("       python {sys.argv[0]} --remove \"Channel Name\"")
        print("       python {sys.argv[0]} --clear")
        print("       python {sys.argv[0]} --list")
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