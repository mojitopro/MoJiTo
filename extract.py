#!/usr/bin/env python3
"""
Extractor de searchtv.net
Ejecutar: python3 extract.py
Guarda en streams.json
"""
import cloudscraper
import urllib.parse
import json

ST = "https://searchtv.net/"

def main():
    scraper = cloudscraper.create_scraper()
    
    # Canales a buscar
    canales = [
        "HBO", "ESPN", "Adult Swim", "TNT", "Space", "Cinecanal", "Golden",
        "Star Channel", "Paramount", "AMC", "Universal", "FX", "Sony", "AXN",
        "Cinemax", "TBS", "Comedy Central", "Discovery", "Nat Geo", "Disney",
        "Nickelodeon", "Cartoon Network", "CNN", "MTV", "VH1"
    ]
    
    todos = {}
    
    for q in canales:
        print(f"Buscando: {q}...", end=" ")
        try:
            resp = scraper.get(f"{ST}search/?query={urllib.parse.quote(q)}", timeout=30)
            if resp.status_code != 200:
                print(f"error {resp.status_code}")
                continue
                
            items = resp.json()
            print(f"{len(items)} resultados")
            
            for item_id, info in items.items():
                # Obtener stream URL
                try:
                    st = scraper.get(f"{ST}stream/uuid/{item_id}/", timeout=20)
                    if st.status_code == 200 and '#EXTM3U' in st.text:
                        for line in st.text.strip().split('\n'):
                            if line.startswith('http'):
                                url = line.strip()
                                name = info.get('title', q).split(' - ')[0].strip()
                                
                                if name not in todos:
                                    todos[name] = {'name': name, 'urls': [], 'category': 'Peliculas'}
                                todos[name]['urls'].append(url)
                                break
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"fail: {e}")
            continue
    
    # Guardar
    result = list(todos.values())
    with open('streams.json', 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"\nGuardado: {len(result)} canales en streams.json")

if __name__ == "__main__":
    main()