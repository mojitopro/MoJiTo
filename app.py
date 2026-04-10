from flask import Flask, jsonify, request, send_from_directory
import os

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MOCK_STREAMS = [
    {"title": "ESPN HD", "url": "https://stream.example.com/espn.m3u8"},
    {"title": "Fox Sports", "url": "https://stream.example.com/foxsports.m3u8"},
    {"title": "Sky Sports", "url": "https://stream.example.com/skysports.m3u8"},
    {"title": "bein sports", "url": "https://stream.example.com/bein.m3u8"},
    {"title": "TNT Sports", "url": "https://stream.example.com/tnt.m3u8"},
    {"title": "ESPN 2", "url": "https://stream.example.com/espn2.m3u8"},
    {"title": "Fox", "url": "https://stream.example.com/fox.m3u8"},
    {"title": "HBO", "url": "https://stream.example.com/hbo.m3u8"},
    {"title": "Star Channel", "url": "https://stream.example.com/star.m3u8"},
    {"title": "FX", "url": "https://stream.example.com/fx.m3u8"},
    {"title": "Universal", "url": "https://stream.example.com/universal.m3u8"},
    {"title": "Warner", "url": "https://stream.example.com/warner.m3u8"},
    {"title": "Sony", "url": "https://stream.example.com/sony.m3u8"},
    {"title": "Paramount", "url": "https://stream.example.com/paramount.m3u8"},
    {"title": "MTV", "url": "https://stream.example.com/mtv.m3u8"},
    {"title": "VH1", "url": "https://stream.example.com/vh1.m3u8"},
    {"title": "Nickelodeon", "url": "https://stream.example.com/nickelodeon.m3u8"},
    {"title": "Cartoon Network", "url": "https://stream.example.com/cartoon.m3u8"},
    {"title": "Disney", "url": "https://stream.example.com/disney.m3u8"},
    {"title": "Discovery", "url": "https://stream.example.com/discovery.m3u8"},
    {"title": "National Geographic", "url": "https://stream.example.com/natgeo.m3u8"},
    {"title": "History", "url": "https://stream.example.com/history.m3u8"},
    {"title": "A&E", "url": "https://stream.example.com/ae.m3u8"},
    {"title": "TLC", "url": "https://stream.example.com/tlc.m3u8"},
    {"title": "CNN", "url": "https://stream.example.com/cnn.m3u8"},
    {"title": "BBC", "url": "https://stream.example.com/bbc.m3u8"},
    {"title": "Fox News", "url": "https://stream.example.com/foxnews.m3u8"},
    {"title": "Al Jazeera", "url": "https://stream.example.com/aljazeera.m3u8"},
    {"title": "E! Entertainment", "url": "https://stream.example.com/e.m3u8"},
    {"title": "Telemundo", "url": "https://stream.example.com/telemundo.m3u8"},
]

@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'tv.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(BASE_DIR, filename)

@app.route('/api/search')
def search():
    query = request.args.get('q', '').lower()
    page = int(request.args.get('page', 1))
    
    if not query:
        filtered = MOCK_STREAMS[:20]
        return jsonify({
            "streams": filtered,
            "hasMore": len(MOCK_STREAMS) > 20
        })
    
    results = [s for s in MOCK_STREAMS if query in s['title'].lower()]
    
    start = (page - 1) * 20
    end = start + 20
    page_results = results[start:end]
    
    return jsonify({
        "streams": page_results,
        "hasMore": end < len(results)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)