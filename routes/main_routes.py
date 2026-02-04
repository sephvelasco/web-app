from flask import Blueprint, render_template, request, jsonify, current_app, session, redirect, url_for
from werkzeug.utils import secure_filename
import os
from models import db
from models.detection import Detection
from datetime import datetime

main_bp = Blueprint('main', __name__)


@main_bp.before_app_request
def require_bogie_verification():
    """Gate access to the main dashboard until the bogie underside is verified."""
    # Allow static/assets and public endpoints
    open_paths = {
        '/',
        '/bogie_check',
        '/set_verified',
        '/verify_image',
        '/video_feed',
        '/usb_video_feed',
        '/live_status',
        '/history',
    }
    if request.path.startswith('/static'):
        return None
    if request.path in open_paths:
        return None

    # Protect dashboard and any future private routes
    if request.path.startswith('/dashboard') and not session.get('bogie_verified'):
        return redirect(url_for('main.precheck'))
    return None


@main_bp.route('/')
def precheck():
    """Pre-check page that verifies the camera is viewing the underside of a train bogie."""
    return render_template('precheck.html')


@main_bp.route('/dashboard')
def dashboard():
    return render_template('index.html')


@main_bp.route('/set_verified', methods=['POST'])
def set_verified():
    """Manually mark the bogie underside as verified (fallback if auto-check is not available)."""
    session['bogie_verified'] = True
    return jsonify({'verified': True})


@main_bp.route('/bogie_check')
def bogie_check():
    """Lightweight pre-check status.

    If you later add a dedicated 'bogie underside' classifier model, you can replace
    the heuristic inside app.py and return a real confidence score.
    """
    # Keep precheck lightweight: app.py maintains bogie status from the USB camera
    helper = getattr(current_app, 'update_bogie_status_from_usb', None)
    if callable(helper):
        helper()

    return jsonify({
        'auto_supported': bool(getattr(current_app, 'bogie_auto_supported', False)),
        'frame_ok': bool(getattr(current_app, 'bogie_frame_ok', False)),
        'verified': bool(session.get('bogie_verified', False)),
        'message': getattr(current_app, 'bogie_message', 'Initializing...'),
    })


@main_bp.route('/verify_image', methods=['POST'])
def verify_image():
    """Verify a train bogie using an uploaded image.

    Uses the optional bogie verification YOLO model if installed.
    The model is loaded in app.py and exposed as current_app.bogie_model.
    """
    file = request.files.get('file')
    if not file or file.filename == '':
        return jsonify({'verified': False, 'error': 'No file uploaded'}), 400

    # Ensure upload folder exists
    precheck_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'precheck')
    os.makedirs(precheck_dir, exist_ok=True)

    filename = secure_filename(file.filename)
    # Avoid overwriting by prefixing timestamp
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
    saved_name = f"precheck_{ts}_{filename}"
    filepath = os.path.join(precheck_dir, saved_name)
    file.save(filepath)

    verifier = getattr(current_app, 'bogie_verifier', None)
    if verifier is None:
        return jsonify({
            'verified': False,
            'error': 'Bogie verification model is not installed on this device.',
            'image_url': f"/static/uploads/precheck/{saved_name}",
        }), 501

    try:
        ok, best = verifier(filepath)
        if ok:
            session['bogie_verified'] = True
        return jsonify({
            'verified': bool(ok),
            'best': best,
            'image_url': f"/static/uploads/precheck/{saved_name}",
        })
    except Exception as e:
        return jsonify({
            'verified': False,
            'error': f'Verification failed: {e}',
            'image_url': f"/static/uploads/precheck/{saved_name}",
        }), 500

@main_bp.route('/upload', methods=['POST'])
def upload_image():
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file uploaded'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    detections = current_app.detector.predict(filepath)

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

    Detection.query.filter_by(image_filename=filename).delete()

    for det in detections:
        new_det = Detection(
            image_filename=filename,
            crack_type=det.get('name', 'unknown'),
            confidence=det.get('confidence', 0.0),
            recommendation=recommendation,
            status=status
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
    """Return detection history grouped by saved image (one card per image)."""
    records = Detection.query.order_by(Detection.timestamp.desc()).all()
    grouped = {}
    for det in records:
        key = det.image_filename
        if key not in grouped:
            grouped[key] = {
                'filename': key,
                'image_url': f'/static/uploads/{key}',
                'timestamp': det.timestamp.strftime('%Y-%m-%d %H:%M:%S') if det.timestamp else '',
                # These are per-image summaries (we keep the first/latest row's values)
                'status': det.status or '',
                'recommendation': det.recommendation or '',
                'detections': []
            }

        grouped[key]['detections'].append({
            'crack_type': det.crack_type,
            'confidence': round(float(det.confidence) * 100, 1)
        })

    return jsonify(list(grouped.values()))