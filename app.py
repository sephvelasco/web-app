from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import os
from detector import CrackDetector
from models import db, Detection

# ────────────── Flask Setup ──────────────
app = Flask(__name__, static_url_path='/static')

# Explicit absolute path for SQLite (ensures correct location)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(BASE_DIR, "database.db")

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Upload folder
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize DB
db.init_app(app)

# ────────────── Initialize Database (Flask 3.x compatible) ──────────────
with app.app_context():
    db.create_all()
    print("Database initialized and tables created (if not existing).")

# ────────────── YOLO Detector ──────────────
detector = CrackDetector('model/best.pt')

# ────────────── Routes ──────────────
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

    # Run YOLOv8 detection
    detections = detector.predict(filepath)

    # Store detections in DB
    with app.app_context():
        for det in detections:
            crack_type = det.get('name') or det.get('class', 'unknown')
            confidence = det.get('confidence', 0.0)
            coords = det.get('coords', (None, None))

            new_record = Detection(
                image_filename=filename,
                crack_type=crack_type,
                confidence=confidence,
                gantry_x=coords[0],
                gantry_y=coords[1],
                recommendation="Inspect and monitor fatigue crack propagation"
            )
            db.session.add(new_record)
        db.session.commit()
        print(f"Saved {len(detections)} detections to the database.")

    return jsonify({
        'image_url': f'/static/uploads/{filename}',
        'detections': detections
    })

@app.route('/history')
def history():
    # Get all detections, newest first
    records = Detection.query.order_by(Detection.timestamp.desc()).all()

    # Group by image file (one entry per uploaded image)
    grouped = {}
    for det in records:
        if det.image_filename not in grouped:
            grouped[det.image_filename] = {
                'filename': det.image_filename,
                'image_url': f'/static/uploads/{det.image_filename}',
                'timestamp': det.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'detections': []
            }
        grouped[det.image_filename]['detections'].append({
            'crack_type': det.crack_type,
            'confidence': round(det.confidence * 100, 1)
        })

    return jsonify(list(grouped.values()))

# ────────────── Main ──────────────
if __name__ == '__main__':
    print(f"Database path: {db_path}")
    app.run(debug=True, host='0.0.0.0')