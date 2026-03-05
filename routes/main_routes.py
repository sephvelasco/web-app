from flask import Blueprint, render_template, request, jsonify, current_app, session, redirect, url_for
from werkzeug.utils import secure_filename
import os
import threading
import time
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

    # Protect dashboard and private APIs
    if not session.get('bogie_verified'):
        protected_prefixes = (
            '/dashboard',
            '/scan',
            '/mapping',
            '/bogie',
        )
        if request.path.startswith(protected_prefixes):
            return redirect(url_for('main.precheck'))
    return None


@main_bp.route('/')
def precheck():
    session.pop("bogie_verified", None)
    session.pop("bogie_id", None)
    return render_template('precheck.html')


@main_bp.route('/dashboard')
def dashboard():
    return render_template('index.html')


@main_bp.route('/set_verified', methods=['POST'])
def set_verified():
    """Mark bogie as verified ONLY if live or upload verification has passed."""
    live_ok = bool(getattr(current_app, 'bogie_live_verified', False))
    upload_ok = bool(getattr(current_app, 'bogie_upload_verified', False))

    if not (live_ok or upload_ok):
        session.pop('bogie_verified', None)
        return jsonify({'ok': False, 'message': 'Verification required.'}), 403

    # Accept optional bogie_id from UI (or auto-generate)
    data = request.get_json(silent=True) or {}
    bogie_id = (data.get('bogie_id') or '').strip()

    def _suggest_next_bogie_id() -> str:
        # Find the highest numeric suffix from existing bogie_ids.
        # Format: BOGIE-0001
        try:
            ids = [r[0] for r in db.session.query(Detection.bogie_id).distinct().all()]
        except Exception:
            ids = []
        best = 0
        for v in ids:
            if not v:
                continue
            s = str(v)
            if s.upper().startswith('BOGIE-'):
                tail = s.split('-', 1)[1]
                try:
                    n = int(tail)
                    best = max(best, n)
                except Exception:
                    continue
        return f"BOGIE-{best+1:04d}"

    if not bogie_id:
        bogie_id = _suggest_next_bogie_id()

    session['bogie_verified'] = True
    session['bogie_id'] = bogie_id

    # Also store on the Flask app for background threads (no session access there)
    try:
        current_app.current_bogie_id = bogie_id
    except Exception:
        pass

    return jsonify({'ok': True, 'bogie_id': bogie_id})


@main_bp.route('/bogie/suggest_id')
def bogie_suggest_id():
    """Suggest the next bogie ID (does not modify session)."""
    try:
        ids = [r[0] for r in db.session.query(Detection.bogie_id).distinct().all()]
    except Exception:
        ids = []
    best = 0
    for v in ids:
        if not v:
            continue
        s = str(v)
        if s.upper().startswith('BOGIE-'):
            tail = s.split('-', 1)[1]
            try:
                n = int(tail)
                best = max(best, n)
            except Exception:
                continue
    return jsonify({'ok': True, 'suggested': f"BOGIE-{best+1:04d}"})


@main_bp.route('/bogie/current')
def bogie_current():
    return jsonify({'ok': True, 'bogie_id': session.get('bogie_id')})


@main_bp.route('/reset', methods=['POST'])
def reset_flow():
    """Reset the web flow back to bogie verification (history is retained)."""
    session.pop('bogie_verified', None)
    session.pop('bogie_id', None)
    # Best-effort reset scan state
    try:
        app = current_app._get_current_object()
        if hasattr(app, 'scan_state') and isinstance(app.scan_state, dict):
            app.scan_state.update({
                'running': False,
                'phase': 'idle',
                'progress': 0.0,
                'message': 'Reset.',
                'stop_requested': False,
                'segment': None,
                'segment_offset_mm': 0.0,
            })
    except Exception:
        pass
    return jsonify({'ok': True})


@main_bp.route('/bogie_check')
def bogie_check():
    """Return live precheck status from USB + model/heuristics."""
    helper = getattr(current_app, 'update_bogie_status_from_usb', None)
    if callable(helper):
        helper()

    # These should be set by app.py / usb_camera helper
    live_ok = bool(getattr(current_app, 'bogie_live_verified', False))
    best = getattr(current_app, 'bogie_best', None)

    return jsonify({
    'auto_supported': bool(getattr(current_app, 'bogie_auto_supported', False)),
    'frame_ok': bool(getattr(current_app, 'bogie_frame_ok', False)),
    'live_verified': bool(getattr(current_app, 'bogie_live_verified', False)),
    'best': getattr(current_app, 'bogie_best', None),
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

        # Store upload verification flag (do NOT set session here)
        current_app.bogie_upload_verified = bool(ok)

        return jsonify({
	    'ok': bool(ok),
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

    # Filter out low-confidence detections (never save/show them)
    conf_min = float(current_app.config.get("CONF_MIN", 0.5))
    detections = [d for d in detections if float(d.get("confidence", 0.0) or 0.0) >= conf_min]

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

# -------------------- Scan automation (X-axis only for now) --------------------

def _ensure_scan_state(app):
    if not hasattr(app, "scan_state") or not isinstance(getattr(app, "scan_state"), dict):
        app.scan_state = {
            "running": False,
            "phase": "idle",
            "distance_mm": 0.0,
            "progress": 0.0,
            "message": "",
            "started_ts": 0.0,
            "ended_ts": 0.0,
            "stop_requested": False,
            "segment": None,
            "segment_offset_mm": 0.0,
        }
    return app.scan_state

def _scan_worker(app, distance_mm: float, return_home: bool):
    st = _ensure_scan_state(app)
    st["running"] = True
    st["phase"] = "forward"
    st["distance_mm"] = float(distance_mm)
    st["progress"] = 0.0
    st["message"] = "Moving forward..."
    st["started_ts"] = time.time()
    st["ended_ts"] = 0.0
    st["stop_requested"] = False

    # Store current segment metadata on app (background threads don't have session)
    try:
        app.current_segment = int(st.get('segment')) if st.get('segment') is not None else None
    except Exception:
        app.current_segment = None
    try:
        app.current_segment_offset_mm = float(st.get('segment_offset_mm', 0.0) or 0.0)
    except Exception:
        app.current_segment_offset_mm = 0.0

    motor = getattr(app, "motor", None)
    if motor is None:
        st["message"] = "Motor serial not initialized."
        st["running"] = False
        st["phase"] = "error"
        st["ended_ts"] = time.time()
        return

    # Command forward move
    try:
        motor.send(f"MOVEMM mm={distance_mm}")
    except Exception as e:
        st["message"] = f"Failed to send motor command: {e}"
        st["running"] = False
        st["phase"] = "error"
        st["ended_ts"] = time.time()
        return
    # Wait until motor finishes or stop requested
    t0 = time.time()
    while True:
        if st.get("stop_requested"):
            st["message"] = "Stop requested."
            break
        ms = motor.get_state()
        # update progress from posMm if available
        try:
            pos = float(ms.get("posMm", 0.0) or 0.0)
            if distance_mm != 0:
                st["progress"] = max(0.0, min(1.0, pos / float(distance_mm)))
        except Exception:
            pass

        if not ms.get("moving", False):
            # If we never got moving=true, allow a tiny grace period after sending command
            if time.time() - t0 > 0.5:
                break
        time.sleep(0.1)

    # Return home (optional)
    if return_home and not st.get("stop_requested"):
        # Pause a bit before returning (operator preference)
        try:
            pause_s = float(os.environ.get('SCAN_RETURN_PAUSE_SEC', '3'))
        except Exception:
            pause_s = 3.0
        if pause_s > 0:
            st["message"] = f"Pausing {pause_s:.0f}s before return..."
            t_pause = time.time()
            while (time.time() - t_pause) < pause_s:
                if st.get('stop_requested'):
                    break
                time.sleep(0.1)

        st["phase"] = "return"
        st["message"] = "Returning to start..."
        motor.send(f"MOVEMM mm={-float(distance_mm)}")
        t1 = time.time()
        while True:
            if st.get("stop_requested"):
                st["message"] = "Stop requested."
                break
            ms = motor.get_state()
            if not ms.get("moving", False):
                if time.time() - t1 > 0.5:
                    break
            time.sleep(0.1)

    st["running"] = False
    st["phase"] = "stopped" if st.get("stop_requested") else "done"
    st["message"] = "Stopped." if st.get("stop_requested") else "Scan complete."
    st["progress"] = 1.0 if st["phase"] == "done" else st.get("progress", 0.0)
    st["ended_ts"] = time.time()


@main_bp.route("/scan/start", methods=["POST"])
def scan_start():
    # IMPORTANT: current_app is a LocalProxy. We must grab the real Flask app
    # object before starting a background thread, otherwise the worker thread
    # can crash with "working outside of application context".
    app = current_app._get_current_object()
    st = _ensure_scan_state(app)

    if st.get("running"):
        return jsonify({"ok": False, "error": "Scan already running", "state": st}), 409

    data = request.get_json(silent=True) or {}
    distance_mm = float(data.get("distance_mm", 950.0))
    return_home = bool(data.get("return_home", True))

    # Segment selection (for 2-pass scan stitching)
    seg = data.get('segment', 1)
    try:
        seg = int(seg)
    except Exception:
        seg = 1
    if seg not in (1, 2):
        seg = 1
    st['segment'] = seg
    st['segment_offset_mm'] = 0.0 if seg == 1 else float(distance_mm)
    session['current_segment'] = seg

    # Store on app for background usage
    try:
        app.current_segment = seg
        app.current_segment_offset_mm = float(st['segment_offset_mm'])
    except Exception:
        pass

    t = threading.Thread(target=_scan_worker, args=(app, distance_mm, return_home), daemon=True)
    app.scan_thread = t
    t.start()

    return jsonify({"ok": True, "state": st})


@main_bp.route("/scan/stop", methods=["POST"])
def scan_stop():
    app = current_app._get_current_object()
    st = _ensure_scan_state(app)
    st["stop_requested"] = True
    motor = getattr(app, "motor", None)
    try:
        if motor:
            motor.send("s")
    except Exception:
        pass
    return jsonify({"ok": True, "state": st})


@main_bp.route("/scan/status", methods=["GET"])
def scan_status():
    st = _ensure_scan_state(current_app)
    # include motor status snapshot too
    motor = getattr(current_app, "motor", None)
    motor_state = motor.get_state() if motor else {}
    return jsonify({"ok": True, "state": st, "motor": motor_state})


@main_bp.route('/mapping/points', methods=['GET'])
def mapping_points():
    """Return mapping points grouped by saved image for the current bogie.

    Each item corresponds to one saved image (marker in 3D viewer).
    """
    bogie_id = request.args.get('bogie_id') or session.get('bogie_id')
    if not bogie_id:
        return jsonify({'ok': True, 'bogie_id': None, 'points': []})

    # Query newest first
    rows = (
        Detection.query
        .filter(Detection.bogie_id == bogie_id)
        .order_by(Detection.timestamp.desc())
        .all()
    )

    grouped = {}
    for det in rows:
        key = det.image_filename
        if key not in grouped:
            grouped[key] = {
                'filename': key,
                'image_url': f'/static/uploads/{key}',
                'timestamp': det.timestamp.strftime('%Y-%m-%d %H:%M:%S') if det.timestamp else '',
                'status': det.status or '',
                'recommendation': det.recommendation or '',
                'bogie_id': det.bogie_id,
                'segment': det.segment,
                'x_mm': float(det.gantry_x) if det.gantry_x is not None else None,
                'y_mm': float(det.gantry_y) if det.gantry_y is not None else None,
                'camera_id': det.camera_id,
                'detections': [],
            }

        grouped[key]['detections'].append({
            'crack_type': det.crack_type,
            'confidence': round(float(det.confidence) * 100, 1),
        })

    pts = list(grouped.values())
    return jsonify({'ok': True, 'bogie_id': bogie_id, 'points': pts})
