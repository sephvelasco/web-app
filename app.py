from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import os
from detector import CrackDetector

app = Flask(__name__, static_url_path='/static')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize YOLOv8 detector
detector = CrackDetector('model/best.pt')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # Run detection
    detections = detector.predict(filepath)

    return jsonify({
        'image_url': f'/static/uploads/{filename}',
        'detections': detections
    })

@app.route('/history')
def history():
    uploads_dir = os.path.join(app.static_folder, 'uploads')
    images = [
        {'filename': f, 'path': f'/static/uploads/{f}'}
        for f in os.listdir(uploads_dir)
        if f.lower().endswith(('.png', '.jpg', '.jpeg'))
    ]
    return jsonify(images)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')