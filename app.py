#!/usr/bin/env python3
from flask import Flask, request, jsonify, send_file
import os

app = Flask(__name__)

@app.route('/')
def index():
    return send_file('tv.html')

if __name__ == '__main__':
    print('MoJiTo TV - IPTV')
    app.run(host='0.0.0.0', port=8080, threaded=True)