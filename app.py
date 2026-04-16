#!/usr/bin/env python3
import os
from pathlib import Path
from flask import Flask, request, jsonify, redirect, send_file

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent

def wants_premium_only():
    category = request.args.get('category', '').strip().lower()
    premium_flag = request.args.get('premium', '').strip().lower()
    mode = request.args.get('mode', '').strip().lower()

    if category in {'premium', 'on-demand', 'ondemand', 'vod'}:
        return True
    if premium_flag in {'1', 'true', 'yes', 'on'}:
        return True
    if mode in {'premium', 'on-demand', 'ondemand'}:
        return True
    return False

def is_legacy_browser(ua):
    """
    Detecta navegadores antiguos de TV que necesitan la version legacy.
    Incluye:
    - Navegadores basados en WebKit antiguos
    - Tizen/WebOS antiguos
    - Navegadores sin soporte para ES6
    - TVs Samsung, LG, Sony antiguas
    """
    ua_lower = ua.lower()
    
    # Lista de navegadores/dispositivos que necesitan version legacy
    legacy_keywords = [
        'webkit/5',
        'applewebkit/5',
        'samsung',
        'smarttv',
        'smart-tv',
        'tizen',
        'webos',
        'netcast',
        'hbbtv',
        'philco',
        'sony dtv',
        'sonycebrowser',
        'opera tv',
        'opr/',
        'es50',
        'msie',
        'trident/',
        'netfront',
        'uc browser',
        'polaris',
        'maui',
    ]
    
    # Verificar si es un navegador legacy
    for keyword in legacy_keywords:
        if keyword in ua_lower:
            return True
    
    # Verificar version de WebKit
    # WebKit versiones anteriores a 537 necesitan legacy
    import re
    webkit_match = re.search(r'applewebkit/(\d+)', ua_lower)
    if webkit_match:
        webkit_version = int(webkit_match.group(1))
        if webkit_version < 537:
            return True
    
    # Verificar Chrome antiguo (< 50)
    chrome_match = re.search(r'chrome/(\d+)', ua_lower)
    if chrome_match:
        chrome_version = int(chrome_match.group(1))
        if chrome_version < 50:
            return True
    
    # Verificar Firefox antiguo (< 45)
    firefox_match = re.search(r'firefox/(\d+)', ua_lower)
    if firefox_match:
        firefox_version = int(firefox_match.group(1))
        if firefox_version < 45:
            return True
    
    return False

def get_device_type():
    ua = request.headers.get('User-Agent', '').lower()
    
    # Palabras clave para detectar TV
    tv_keywords = [
        'smarttv', 'smart-tv', 'philco', 'googletv', 'appletv', 
        'roku', 'chromecast', 'tizen', 'webos', 'netcast', 'hbbtv',
        'samsung', 'lge', 'lg-', 'sony dtv', 'bravia', 'viera',
        'netflix', 'tv store', 'opera tv', 'vidaa'
    ]
    
    # Palabras clave para excluir mobiles
    mobile_keywords = ['android mobile', 'iphone', 'ipad', 'ipod', 'mobile', 'tablet']
    
    # Verificar si es TV
    for keyword in tv_keywords:
        if keyword in ua:
            # Excluir si es un movil/tablet
            is_mobile = any(m in ua for m in mobile_keywords)
            if not is_mobile:
                return 'tv'
    
    # Verificar mobile
    if any(x in ua for x in ['android', 'iphone', 'ipad', 'ipod', 'mobile', 'tablet']):
        return 'mobile'
    
    # Por defecto, tratar como TV para mejor experiencia
    return 'tv'

def get_html_version():
    """
    Determina que version HTML servir basado en el User-Agent.
    Retorna: 'pluto', 'legacy' o 'modern'
    """
    ua = request.headers.get('User-Agent', '')
    
    # Parametro explicito para forzar version
    version = request.args.get('version', '').strip().lower()
    if version in {'pluto', 'tv'}:
        return 'pluto'
    if version in {'legacy', 'old', 'es5'}:
        return 'legacy'
    if version in {'modern', 'new', 'es6'}:
        return 'modern'
    
    # Por defecto, usar pluto (estilo Pluto TV) para maxima compatibilidad
    return 'pluto'

@app.route('/')
def index():
    device = get_device_type()
    html_version = get_html_version()
    
    # Servir version pluto por defecto
    if html_version == 'pluto':
        return send_file(str(BASE_DIR / 'tv-pluto.html'))
    if html_version == 'legacy':
        return send_file(str(BASE_DIR / 'tv-legacy.html'))
    
    if device == 'mobile':
        return send_file(str(BASE_DIR / 'mobile.html'))
    return send_file(str(BASE_DIR / 'tv.html'))

@app.route('/tv.html')
@app.route('/tv')
def tv():
    html_version = get_html_version()
    if html_version == 'pluto':
        return send_file(str(BASE_DIR / 'tv-pluto.html'))
    if html_version == 'legacy':
        return send_file(str(BASE_DIR / 'tv-legacy.html'))
    return send_file(str(BASE_DIR / 'tv.html'))

@app.route('/pluto')
@app.route('/tv-pluto.html')
def tv_pluto():
    return send_file(str(BASE_DIR / 'tv-pluto.html'))

@app.route('/tv-legacy.html')
@app.route('/legacy')
def tv_legacy():
    return send_file(str(BASE_DIR / 'tv-legacy.html'))

@app.route('/tv-addictive.html')
@app.route('/tv-addictive')
def tv_addictive():
    return redirect('/tv', code=302)

@app.route('/api/channels')
def api_channels():
    from selector import get_all_channels
    premium_only = wants_premium_only()
    sort_by = request.args.get('sort', 'latency').strip().lower()
    limit = request.args.get('limit', type=int)
    channels = get_all_channels(limit=limit, premium_only=premium_only, sort_by=sort_by)

    return jsonify({
        'status': 'ok',
        'category': 'premium' if premium_only else 'all',
        'sort': sort_by,
        'channels': channels,
    })

@app.route('/api/stream/<path:channel>')
@app.route('/api/channel/<path:channel>')
def api_stream(channel):
    from selector import get_best_stream
    result = get_best_stream(channel, premium_only=wants_premium_only())
    if result:
        return jsonify({
            'status': 'ok',
            'stream': result,
            **result
        })
    return jsonify({
        'status': 'error',
        'error': 'channel not found',
        'url': None,
        'fallbacks': []
    })

@app.route('/api/search')
def api_search():
    from selector import search_channels
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({
            'status': 'ok',
            'streams': [],
        })
    premium_only = wants_premium_only()
    results = search_channels(q, premium_only=premium_only)
    return jsonify({
        'status': 'ok',
        'premium_only': premium_only,
        'streams': results,
    })

@app.route('/api/stats')
def api_stats():
    from selector import get_stats
    return jsonify(get_stats())

@app.route('/api/debug')
def api_debug():
    ua = request.headers.get('User-Agent', '')
    return jsonify({
        'user_agent': ua,
        'detected_device': get_device_type(),
        'is_legacy': is_legacy_browser(ua),
        'html_version': get_html_version()
    })

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'mojito-tv'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, threaded=True, debug=False)
