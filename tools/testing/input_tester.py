#!/usr/bin/env python3
"""
CLI Input Tester para MoJiTo TV
Ejecuta esto y abre http://TU_IP:8081 en la TV
Luego presiona las teclas del control remoto y dime qué aparece aquí
"""
import os
import json
from pathlib import Path
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

REGISTERED_KEYS = {}
HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>MoJiTo - Input Tester</title>
    <style>
        body {
            background: #111;
            color: #0f0;
            font-family: monospace;
            padding: 20px;
            font-size: 24px;
        }
        .key-display {
            border: 3px solid #0f0;
            padding: 30px;
            margin: 20px 0;
            min-height: 100px;
        }
        .received {
            color: #ff0;
            font-size: 30px;
        }
        .log {
            font-size: 16px;
            color: #888;
            max-height: 300px;
            overflow-y: scroll;
        }
        .log-item {
            padding: 5px;
            border-bottom: 1px solid #333;
        }
    </style>
</head>
<body>
    <h1>⭳ INPUT TESTER</h1>
    <p>Presiona las teclas de tu control remoto Philco</p>
    
    <div class="key-display" id="keyDisplay">
        <span style="color:#666">Esperando input...</span>
    </div>
    
    <h2>LOG:</h2>
    <div class="log" id="log"></div>
    
    <script>
        var keys = [];
        
        document.addEventListener('keydown', function(e) {
            e.preventDefault();
            
            var info = {
                key: e.key,
                code: e.code,
                keyCode: e.keyCode,
                bubbles: e.bubbles,
                time: new Date().toISOString()
            };
            
            keys.push(info);
            
            document.getElementById('keyDisplay').innerHTML = 
                '<span class="received">Recibido: ' + JSON.stringify(info) + '</span>';
            
            // Send to server
            fetch('/log', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(info)
            });
            
            // Update log
            var logDiv = document.getElementById('log');
            logDiv.innerHTML = '<div class="log-item">' + JSON.stringify(info) + '</div>' + logDiv.innerHTML;
        });
        
        // Also capture regular clicks/taps
        document.addEventListener('click', function(e) {
            var info = {
                type: 'click',
                target: e.target.tagName,
                clientX: e.clientX,
                clientY: e.clientY,
                time: new Date().toISOString()
            };
            
            fetch('/log', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(info)
            });
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return HTML

@app.route('/log', methods=['POST'])
def log_key():
    data = request.json
    print(f"\n>>> INPUT RECIBIDO: {data}")
    return jsonify({'status': 'ok'})

@app.route('/keys')
def get_keys():
    return jsonify(REGISTERED_KEYS)

print("""
╔════════════════════════════════════════╗
║    MoJiTo TV INPUT TESTER           ║
╠══════════���═════════════════════════════╣
║ 1. Ejecuta este script              ║
║ 2. Abre en la TV: http://IP:8081     ║
║ 3. Presiona las teclas del remote   ║
║ 4. Lee los inputs aquí              ║
╚════════════════════════════════════════╝
""")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8081))
    print(f"\nIniciando en http://0.0.0.0:{port}")
    print(f"Abre en tu navegador: http://TU_IP:{port}\n")
    app.run(host='0.0.0.0', port=port, debug=False)