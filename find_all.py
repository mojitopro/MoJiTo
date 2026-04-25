import requests
import subprocess
import json

BASE = "https://raw.githubusercontent.com/iptv-org/iptv/refs/heads/master"
PAISES = ['co', 'mx', 'ar', 've', 'pe', 'cl', 'us', 'do', 'cr', 'gt', 'hn', 'sv', 'ni', 'py', 'uy', 'ec']
SEARCH = ['ESPN', 'HBO', 'TNT', 'SPACE', 'GOLDEN', 'STAR', 'AMC', 'UNIVERSAL', 'FX', 'SONY', 'AXN', 'CINEMAX']

all_found = {}

for pais in PAISES:
    url = f"{BASE}/streams/{pais}.m3u"
    try:
        r = requests.get(url, timeout=8)
        if r.status_code != 200:
            continue
        lines = r.text.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('#EXTINF:'):
                nom = line.split(',')[-1].strip() if ',' in line else ''
                for s in SEARCH:
                    if s.upper() in nom.upper():
                        if i+1 < len(lines):
                            stream_url = lines[i+1].strip()
                            if stream_url.startswith('http'):
                                if s not in all_found:
                                    all_found[s] = []
                                all_found[s].append(stream_url)
    except:
        pass

print(f"Encontrados: {len(all_found)}")
for c, urls in all_found.items():
    print(f" {c}: {len(urls)} URLs")

# Testear todos
print("\nTesteando...")
working = []
tested = set()
for canal, urls in all_found.items():
    for url in urls[:10]:
        if url in tested:
            continue
        tested.add(url)
        try:
            r = subprocess.run(['curl', '-sI', '--max-time', '3', url], capture_output=True, timeout=4)
            if '200' in r.stdout or '301' in r.stdout:
                working.append({
                    'name': canal,
                    'url': url,
                    'backups': urls[:5],
                    'category': 'Peliculas'
                })
                print(f"OK: {canal}")
                break
        except:
            pass

# Si no hay, buscar en otras fuentes
if not working:
    print("\nBuscando fuentes alternativas...")
    others = [
        "https://github.com/Free-TV/IPTV/raw/refs/heads/master/playlist.m3u8",
    ]
    for o in others:
        try:
            r = requests.get(o, timeout=10)
            if r.status_code != 200:
                continue
            lines = r.text.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('#EXTINF:'):
                    nom = line.split(',')[-1].strip() if ',' in line else ''
                    for s in SEARCH:
                        if s.upper() in nom.upper():
                            if i+1 < len(lines):
                                url = lines[i+1].strip()
                                if url.startswith('http'):
                                    if s not in [ch.get('name') for ch in working]:
                                        working.append({
                                            'name': s,
                                            'url': url,
                                            'backups': [url],
                                            'category': 'Peliculas'
                                        })
                                        print(f"OK: {s}")
        except:
            pass

print(f"\nTotal: {len(working)} canales")

with open('custom_channels.json', 'w') as f:
    json.dump(working, f, indent=2)

print("Guardado")