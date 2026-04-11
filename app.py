#!/usr/bin/env python3
from flask import Flask, request, jsonify, send_file
import os

app = Flask(__name__)

@app.route('/')
def index():
    return send_file(os.path.join(os.path.dirname(__file__), 'tv.html'))

if __name__ == '__main__':
    print('MoJiTo TV')
    app.run(host='0.0.0.0', port=8080, threaded=True, debug=False)