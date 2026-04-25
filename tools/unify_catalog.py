#!/usr/bin/env python3
"""Unifica todas las streams de todas las fuentes en un solo catálogo"""
import json
import os
from pathlib import Path

ROOT = Path('/data/data/com.termux/files/home/MoJiTo')
OUTPUT_FILE = ROOT / 'unified_catalog.json'

ALL_CHANNELS = []

def add_channel(name, url, category, channel_type, fallbacks=None):
    """Agrega un canal al catálogo unificado"""
    key = name.lower().strip()
    
    existing = next((i for i, ch in enumerate(ALL_CHANNELS) if ch['name'].lower() == key), None)
    
    if existing is not None:
        if url not in ALL_CHANNELS[existing]['urls']:
            ALL_CHANNELS[existing]['urls'].append(url)
        if fallbacks:
            for fb in fallbacks:
                if fb not in ALL_CHANNELS[existing]['urls']:
                    ALL_CHANNELS[existing]['urls'].append(fb)
        if channel_type not in ALL_CHANNELS[existing]['types']:
            ALL_CHANNELS[existing]['types'].append(channel_type)
        if category and not ALL_CHANNELS[existing]['category']:
            ALL_CHANNELS[existing]['category'] = category
    else:
        ALL_CHANNELS.append({
            'name': name.strip(),
            'category': category or 'General',
            'types': [channel_type],
            'urls': [url] + (fallbacks or [])
        })

def load_premium():
    """Carga premium_working.json"""
    print("Cargando premium_working.json...")
    try:
        with open(ROOT / 'premium_working.json') as f:
            data = json.load(f)
        for ch in data.get('channels', []):
            name = ch.get('name', '')
            url = ch.get('url', '')
            category = ch.get('category', '')
            fallbacks = ch.get('fallbacks', [])
            if name and url:
                add_channel(name, url, category, 'premium', fallbacks)
        print(f"  + {len(data.get('channels', []))} canales premium")
    except Exception as e:
        print(f"  Error: {e}")

def load_custom():
    """Carga custom_channels.json"""
    print("Cargando custom_channels.json...")
    try:
        with open(ROOT / 'custom_channels.json') as f:
            data = json.load(f)
        for ch in data:
            name = ch.get('name', '')
            url = ch.get('url', '')
            category = ch.get('category', 'Custom')
            fallbacks = ch.get('backups', [])
            if name and url:
                add_channel(name, url, category, 'custom', fallbacks)
        print(f"  + {len(data)} canales custom")
    except Exception as e:
        print(f"  Error: {e}")

def load_working():
    """Carga working_streams.json"""
    print("Cargando working_streams.json...")
    try:
        with open(ROOT / 'working_streams.json') as f:
            data = json.load(f)
        if isinstance(data, list):
            ch_list = data
        else:
            ch_list = data.get('channels', [])
        for ch in ch_list:
            name = ch.get('name', '')
            url = ch.get('url', '')
            category = ch.get('category', '')
            fallbacks = ch.get('fallbacks', [])
            if name and url:
                add_channel(name, url, category, 'normal', fallbacks)
        print(f"  + {len(ch_list)} canales normal")
    except Exception as e:
        print(f"  Error: {e}")

def load_verified():
    """Carga canales verificados manualmente"""
    print("Cargando canales verificados...")
    verified = [
        {"name": "Adult Swim", "url": "http://190.60.59.67:8000/play/a0io", "category": "Infantil"},
        {"name": "Adult Swim", "url": "http://181.119.86.1:8000/play/a019", "category": "Infantil"},
        {"name": "Adult Swim", "url": "http://190.61.42.218:9000/play/a06r", "category": "Infantil"},
        {"name": "Adult Swim", "url": "http://181.78.79.131:8000/play/a0pk", "category": "Infantil"},
    ]
    for v in verified:
        add_channel(v['name'], v['url'], v['category'], 'verified', [])
    print(f"  + {len(verified)} canales verificados")

def save_catalog():
    """Guarda el catálogo unificado"""
    catalog = {
        "catalog_version": "1.0.0",
        "updated": "2026-04-25",
        "description": "Catálogo unificado: premium + custom + normal + verified",
        "total_channels": len(ALL_CHANNELS),
        "channel_types": {
            "premium": len([c for c in ALL_CHANNELS if 'premium' in c['types']]),
            "custom": len([c for c in ALL_CHANNELS if 'custom' in c['types']]),
            "normal": len([c for c in ALL_CHANNELS if 'normal' in c['types']]),
            "verified": len([c for c in ALL_CHANNELS if 'verified' in c['types']])
        },
        "channels": ALL_CHANNELS
    }
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(catalog, f, indent=2)
    
    print(f"\n=== CATÁLOGO UNIFICADO ===")
    print(f"Total canales: {len(ALL_CHANNELS)}")
    print(f"  - Premium: {catalog['channel_types']['premium']}")
    print(f"  - Custom: {catalog['channel_types']['custom']}")
    print(f"  - Normal: {catalog['channel_types']['normal']}")
    print(f"  - Verified: {catalog['channel_types']['verified']}")
    print(f"\nGuardado en: {OUTPUT_FILE}")

def main():
    print("Unificando streams...\n")
    load_premium()
    load_custom()
    load_working()
    load_verified()
    save_catalog()
    
    print("\n=== PRIMEROS 20 CANALES ===")
    for ch in ALL_CHANNELS[:20]:
        types_str = ", ".join(ch['types'])
        print(f"  {ch['name']} ({types_str}) - {len(ch['urls'])} URLs")

if __name__ == '__main__':
    main()