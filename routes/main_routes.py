from flask import Blueprint, render_template, request, jsonify, current_app
from werkzeug.utils import secure_filename
import os
from services.detector_service import CrackDetector
from models import db
from models.detection import Detection
from datetime import datetime

main_bp = Blueprint('main', __name__)

# Initialize YOLO
detector = CrackDetector('model/best.pt')

@main_bp.route('/')
def dashboard():
    return render_template('index.html')

@main_bp.route('/upload', methods=['POST'])
def upload_image():
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file uploaded'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    detections = detector.predict(filepath)

    # Determine crack types
    crack_types = [det.get('name', 'unknown').lower() for det in detections]
    status = "Normal"
    recommendation = "No significant defects detected."

    if "transverse" in crack_types and "longitudinal" in crack_types:
        status = "For Replacement"
        recommendation = "Replace Train Bogie Frame"
    elif "transverse" in crack_types:
        status = "For Replacement"
        recommendation = "Replace Train Bogie Frame"
    elif "longitudinal" in crack_types:
        status = "For Repair"
        recommendation = "Reweld Area Along The Crack"

    # Save detections in DB
    for det in detections:
        new_det = Detection(
            image_filename=filename,
            crack_type=det.get('name', 'unknown'),
            confidence=det.get('confidence', 0.0),
            recommendation=recommendation
        )
        db.session.add(new_det)
    db.session.commit()

    return jsonify({
        'image_url': f'/static/uploads/{filename}',
        'detections': detections,
        'status': status,
        'recommendation': recommendation,
        'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    })

@main_bp.route('/history')
def history():
    records = Detection.query.order_by(Detection.timestamp.desc()).all()
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