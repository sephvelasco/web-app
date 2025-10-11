from flask import Flask, render_template, jsonify
import os, json
from model.inference import get_latest_detections

app = Flask(__name__, static_folder='static', template_folder='templates')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data/latest')
def latest_data():
    # You can later replace this with live inference results
    detections = get_latest_detections()
    return jsonify(detections)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)