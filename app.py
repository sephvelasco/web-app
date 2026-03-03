from flask import Flask, render_template, request, jsonify, Response, current_app
from werkzeug.utils import secure_filename
from models import db
from services.detector_service import CrackDetector
from services.usb_camera import USBCamera, discover_usb_video_device
from services.motor_serial import MotorSerialManager
from models.detection import Detection
from routes.main_routes import main_bp
from routes.motor_routes import motor_bp
from datetime import datetime
import io
import os
import cv2
import numpy as np
import time
import atexit

# Optional: bogie verification model (YOLOv8)
try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except Exception:
    ULTRALYTICS_AVAILABLE = False

# Only import picamera2 if available
try:
    from picamera2 import Picamera2
    PICAMERA_AVAILABLE = True
except ImportError:
    PICAMERA_AVAILABLE = False

app = Flask(__name__, static_url_path='/static')
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-change-me')

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(BASE_DIR, "database.db")

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)


# ---------------- Motor Serial (Arduino) ----------------
# Keep the serial port open for the life of the app so UI can control the TB6600 driver via Arduino.
motor = MotorSerialManager(port=os.environ.get("ARDUINO_PORT", "/dev/ttyACM0"), baud=115200)
motor.start()
app.motor = motor

@atexit.register
def _close_motor_serial():
    try:
        app.motor.close()
    except Exception:
        pass


# Initialize crack detection model (dashboard)
CRACK_MODEL_PATH = os.environ.get('CRACK_MODEL_PATH', os.path.join(BASE_DIR, 'model', 'crack.pt'))
detector = CrackDetector(CRACK_MODEL_PATH)

app.detector = detector

app.latest_detections = []
app.latest_recommendation = "No data"
app.latest_status = "Idle"
app.latest_frame_jpeg = None
app.detection_enabled = True   # live detection is enabled by default

# Pre-check (bogie underside verification) signals
app.bogie_frame_ok = False
app.bogie_message = "Initializing cameras..."
app.bogie_auto_supported = False  # flips True if bogie verification model is loaded

# Gate state for precheck (live + upload)
app.bogie_live_verified = False
app.bogie_upload_verified = False
app.bogie_best = None

# Precheck verification model (precheck page + upload verification)
PRECHECK_MODEL_PATH = os.environ.get('PRECHECK_MODEL_PATH', os.path.join(BASE_DIR, 'model', 'precheck.pt'))

# USB camera for bogie verification (Logitech C270 or similar)
USB_VERIFY_DEVICE = os.environ.get('USB_VERIFY_DEVICE', '/dev/video16')
USB_VERIFY_WIDTH = int(os.environ.get('USB_VERIFY_WIDTH', '640'))
USB_VERIFY_HEIGHT = int(os.environ.get('USB_VERIFY_HEIGHT', '480'))
USB_VERIFY_FPS = int(os.environ.get('USB_VERIFY_FPS', '15'))
USB_VERIFY_MJPEG = os.environ.get('USB_VERIFY_MJPEG', '1') != '0'

BOGIE_VERIFY_CONF = float(os.environ.get('BOGIE_VERIFY_CONF', '0.60'))
# Optional allowlist: comma-separated class names that count as "bogie verified"
BOGIE_VERIFY_CLASSES = [
    s.strip().lower() for s in os.environ.get('BOGIE_VERIFY_CLASSES', '').split(',') if s.strip()
]

def _build_bogie_verifier():
    """Returns a callable verifier(image_path|np.ndarray) -> (ok: bool, best: dict|None)."""
    if not ULTRALYTICS_AVAILABLE:
        return None
    if not os.path.exists(PRECHECK_MODEL_PATH):
        return None

    try:
        model = YOLO(PRECHECK_MODEL_PATH)

    except Exception as e:
        print(f"Failed to load precheck model at {PRECHECK_MODEL_PATH}: {e}")
        return None

    def verifier(source):
        # source can be file path or numpy image
        results = model.predict(source, verbose=False)
        r = results[0]
        best = None
        ok = False

        if hasattr(r, 'boxes') and r.boxes is not None and len(r.boxes) > 0:
            boxes = r.boxes
            xyxy = boxes.xyxy
            confs = boxes.conf
            clss = boxes.cls
            # Convert to python lists if tensor-like
            try:
                confs_list = confs.tolist()
                clss_list = clss.tolist()
            except Exception:
                confs_list = list(confs)
                clss_list = list(clss)

            for conf, cls in zip(confs_list, clss_list):
                c = float(conf)
                class_id = int(cls)
                name = r.names[class_id] if hasattr(r, 'names') else str(class_id)
                cand = {'name': str(name), 'conf': c, 'class_id': class_id}
                if (best is None) or (c > best['conf']):
                    best = cand

            # Decide verification
            if best is not None and best['conf'] >= BOGIE_VERIFY_CONF:
                if not BOGIE_VERIFY_CLASSES:
                    # No allowlist provided: accept any confident detection
                    ok = True
                else:
                    ok = best['name'].lower() in BOGIE_VERIFY_CLASSES
        return ok, best

    # expose for routes
    app.bogie_model = model
    return verifier

app.bogie_verifier = _build_bogie_verifier()
if app.bogie_verifier is not None:
    app.bogie_auto_supported = True
    print(f"Bogie verification model loaded: {PRECHECK_MODEL_PATH}")
else:
    print("Bogie verification model not loaded (optional).")

DETECT_EVERY = 3  # run detection every 3 frames for perf
frame_counter = 0

# Auto-save settings (saves detections to History automatically)
AUTO_SAVE_ENABLED = True
AUTO_SAVE_COOLDOWN_SEC = 5
last_auto_save_ts = 0.0
last_auto_save_sig = None

# ---------------- Camera configuration ----------------
cam0 = None
cam1 = None
usb_cam = None
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
is_picamera_initialized = False
DETECTION_ENABLED = False

if PICAMERA_AVAILABLE and os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    try:
        print("Initializing Picamera2 devices...")
        cam0 = Picamera2(0)
        cam0.configure(cam0.create_preview_configuration({"size": (FRAME_WIDTH, FRAME_HEIGHT)}))
        cam0.start()
        cam1 = Picamera2(1)
        cam1.configure(cam1.create_preview_configuration({"size": (FRAME_WIDTH, FRAME_HEIGHT)}))
        cam1.start()
        is_picamera_initialized = True
        print("Cameras initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize Picamera2: {e}")
else:
    print("Skipping Picamera2 initialization (not available or in reloader).")

# Initialize USB verification camera (avoid double-open under Flask reloader)
if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    try:
        # Try preferred device first; if it fails, auto-discover a usable /dev/videoX.
        preferred = USB_VERIFY_DEVICE
        chosen = discover_usb_video_device(preferred=preferred, max_index=30)
        if chosen is None:
            raise RuntimeError(
                f"No usable /dev/videoX found (preferred was {preferred}). "
                "Try: v4l2-ctl --list-devices"
            )

        usb_cam = USBCamera(
            device=chosen,
            width=USB_VERIFY_WIDTH,
            height=USB_VERIFY_HEIGHT,
            fps=USB_VERIFY_FPS,
            use_mjpeg=USB_VERIFY_MJPEG,
        )
        print(f"USB verification camera initialized: {chosen}")
    except Exception as e:
        usb_cam = None
        print(f"USB verification camera not available: {e}")


def update_bogie_status_from_usb():
    """Update live bogie verification status using USB camera + precheck model."""
    # Default to not verified until proven
    app.bogie_live_verified = False
    app.bogie_best = None

    if usb_cam is None:
        app.bogie_frame_ok = False
        app.bogie_message = "USB verification camera not available."
        return

    ret, frame = usb_cam.read()
    if not ret or frame is None:
        app.bogie_frame_ok = False
        app.bogie_message = "Reading USB verification camera..."
        return

    # Optional frame health heuristic (separate from verification)
    try:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        focus_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        non_black = float(np.mean(gray > 15))
        app.bogie_frame_ok = (focus_score > 30.0) and (non_black > 0.05)
    except Exception:
        app.bogie_frame_ok = True

    verifier = getattr(app, 'bogie_verifier', None)
    if verifier is None:
        app.bogie_message = "Precheck model not loaded."
        return

    try:
        ok, best = verifier(frame)
        app.bogie_live_verified = bool(ok)
        app.bogie_best = best                 

        if best and best.get("name"):
            app.bogie_message = f"{best['name']} ({best.get('conf', 0.0):.2f})"
        else:
            app.bogie_message = "Verified" if ok else "Searching for train bogie..."
    except Exception as e:
        app.bogie_live_verified = False
        app.bogie_best = None
        app.bogie_message = f"Precheck model error: {e}"


def generate_usb_frames():
    """MJPEG stream from USB verification camera for the precheck page."""
    while True:
        try:
            if usb_cam is None:
                frame = np.zeros((USB_VERIFY_HEIGHT, USB_VERIFY_WIDTH, 3), dtype=np.uint8)
                cv2.putText(frame, "USB verification camera not available", (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            else:
                ret, frame = usb_cam.read()
                if not ret or frame is None:
                    frame = np.zeros((USB_VERIFY_HEIGHT, USB_VERIFY_WIDTH, 3), dtype=np.uint8)
                    cv2.putText(frame, "Reading USB camera...", (20, 40),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

            ok, buffer = cv2.imencode('.jpg', frame)
            if not ok:
                time.sleep(0.02)
                continue

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        except Exception:
            time.sleep(0.05)
            continue

def generate_frames():
    global frame_counter, last_auto_save_ts, last_auto_save_sig
    # combined width = FRAME_WIDTH * 2
    while True:
        frame_counter += 1
        try:
            f0 = cv2.cvtColor(cam0.capture_array(), cv2.COLOR_RGB2BGR)
            f1 = cv2.cvtColor(cam1.capture_array(), cv2.COLOR_RGB2BGR)
            frame = cv2.hconcat([f0, f1])
        except Exception:
            frame = np.zeros((FRAME_HEIGHT, FRAME_WIDTH * 2, 3), dtype=np.uint8)
            cv2.putText(frame, "Waiting for frames...", (50, FRAME_HEIGHT // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

        # NOTE: Bogie precheck is now driven by the USB verification camera.
        # The CSI cameras are dedicated to crack detection and dashboard streaming.

        # Run detection only every Nth frame to save CPU
        if app.detection_enabled and frame_counter % DETECT_EVERY == 0:
            try:
                # pass numpy array directly to ultralytics YOLO
                results = detector.model.predict(frame, verbose=False)  # using ultralytics API
                res = results[0]
                detections_list = []
                if hasattr(res, "boxes") and res.boxes is not None:
                    boxes = res.boxes  # Ultralytics results object
                    xyxy = boxes.xyxy.numpy() if hasattr(boxes.xyxy, 'numpy') else boxes.xyxy
                    confs = boxes.conf.numpy() if hasattr(boxes.conf, 'numpy') else boxes.conf
                    clss = boxes.cls.numpy() if hasattr(boxes.cls, 'numpy') else boxes.cls
                    for i, (bb, conf, cls) in enumerate(zip(xyxy, confs, clss)):
                        x1, y1, x2, y2 = map(int, bb[:4])
                        class_id = int(cls)
                        name = res.names[class_id] if hasattr(res, 'names') else str(class_id)
                        detections_list.append({
                            'name': name,
                            'confidence': float(conf),
                            'bbox': [x1, y1, x2, y2]
                        })
                        # Draw box on frame
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 200, 0), 2)
                        cv2.putText(frame, f"{name} {conf:.2f}", (x1, max(y1-6,0)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
                else:
                    detections_list = []
            except Exception as e:
                print("Detection error:", e)
                detections_list = []

            # Ignore 'normal' class if your model includes it
            detections_list = [d for d in detections_list if str(d.get('name','')).lower() != 'normal']

        else:
            # Keep last detections if not running detection this frame
            detections_list = app.latest_detections

        crack_types = [d['name'].lower() for d in detections_list]
        if "transverse" in crack_types and "longitudinal" in crack_types:
            app.latest_status = "For Replacement"
            app.latest_recommendation = "Replace Train Bogie Frame"
        elif "transverse" in crack_types:
            app.latest_status = "For Replacement"
            app.latest_recommendation = "Replace Train Bogie Frame"
        elif "longitudinal" in crack_types:
            app.latest_status = "For Repair"
            app.latest_recommendation = "Reweld Area Along The Crack"
        else:
            app.latest_status = "Normal"
            app.latest_recommendation = "No significant defects detected."

        app.latest_detections = [
            {'name': d['name'], 'confidence': round(d['confidence'], 2)}
            for d in detections_list
        ]

        # encode annotated frame to JPEG and save bytes to app.latest_frame_jpeg
        ret, buffer = cv2.imencode('.jpg', frame)
        if ret:
            app.latest_frame_jpeg = buffer.tobytes()

        # --- Auto-save to History when cracks are detected ---
        if (
            AUTO_SAVE_ENABLED
            and app.detection_enabled
            and len(detections_list) > 0
            and ret
        ):
            now = time.time()
            crack_sig = tuple(sorted([d.get('name', '') for d in detections_list]))
            if (now - last_auto_save_ts) >= AUTO_SAVE_COOLDOWN_SEC and crack_sig != last_auto_save_sig:
                try:
                    bogie_id = getattr(app, 'current_bogie_id', None)
                    prefix = str(bogie_id).strip() if bogie_id else 'autosave'
                    # Filename includes bogie id for easier browsing
                    fname = f"{prefix}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.jpg"
                    out_path = os.path.join(app.config['UPLOAD_FOLDER'], fname)
                    with open(out_path, 'wb') as f:
                        f.write(buffer.tobytes())

                    # --- Mapping snapshot (Phase 1) ---
                    seg = getattr(app, 'current_segment', None)
                    try:
                        seg = int(seg) if seg is not None else None
                    except Exception:
                        seg = None
                    seg_offset = getattr(app, 'current_segment_offset_mm', 0.0)
                    try:
                        seg_offset = float(seg_offset or 0.0)
                    except Exception:
                        seg_offset = 0.0

                    # Motor position (mm) from Arduino state
                    x_local_mm = None
                    x_global_mm = None
                    try:
                        ms = app.motor.get_state() if getattr(app, 'motor', None) else {}
                        if ms and ms.get('posMm') is not None:
                            x_local_mm = float(ms.get('posMm'))
                            x_global_mm = x_local_mm + seg_offset
                    except Exception:
                        pass

                    # Simple mm-per-pixel (tunable via env)
                    try:
                        mm_per_px = float(os.environ.get('MAP_MM_PER_PX', '0.5'))
                    except Exception:
                        mm_per_px = 0.5
                    try:
                        side_sep = float(os.environ.get('MAP_SIDE_SEP_MM', '250'))
                    except Exception:
                        side_sep = 250.0

                    with app.app_context():
                        for det in detections_list:
                            bbox = det.get('bbox') or [0, 0, 0, 0]
                            try:
                                x1, y1, x2, y2 = bbox
                                cx = int((int(x1) + int(x2)) / 2)
                                cy = int((int(y1) + int(y2)) / 2)
                            except Exception:
                                cx, cy = 0, 0

                            # Determine which CSI camera the bbox belongs to (combined frame)
                            cam_id = 0 if cx < FRAME_WIDTH else 1
                            local_cx = cx if cam_id == 0 else max(0, cx - FRAME_WIDTH)

                            # Y mapping: center at image mid, multiply by mm/px, then separate L/R
                            try:
                                cx0 = FRAME_WIDTH / 2.0
                                y_mm = (float(local_cx) - cx0) * mm_per_px
                            except Exception:
                                y_mm = 0.0
                            y_mm = float(y_mm)
                            y_mm = y_mm + (-side_sep if cam_id == 0 else side_sep)

                            new_det = Detection(
                                image_filename=fname,
                                crack_type=det.get('name', 'unknown'),
                                confidence=det.get('confidence', 0.0),
                                recommendation=app.latest_recommendation,
                                status=app.latest_status,
                                bogie_id=bogie_id,
                                segment=seg,
                                x_local_mm=x_local_mm,
                                gantry_x=x_global_mm,
                                gantry_y=y_mm,
                                camera_id=cam_id,
                                bbox_cx=cx,
                                bbox_cy=cy,
                            )
                            db.session.add(new_det)
                        db.session.commit()

                    last_auto_save_ts = now
                    last_auto_save_sig = crack_sig
                except Exception as e:
                    print("Auto-save error:", e)

        yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n'

@app.route("/toggle_detection", methods=["POST"])
def toggle_detection():
    """Toggle real-time crack detection."""
    app.detection_enabled = not getattr(app, "detection_enabled", True)
    return jsonify({"detection_enabled": app.detection_enabled})

@app.route("/video_feed")
def video_feed():
    return Response(generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/usb_video_feed")
def usb_video_feed():
    return Response(generate_usb_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route('/live_status')
def live_status():
    # return latest info for dashboard polling
    return jsonify({
        'detections': current_app.latest_detections,
        'status': current_app.latest_status,
        'recommendation': current_app.latest_recommendation,
        'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/capture', methods=['POST'])
def capture():
    """ Save the most recent annotated frame to disk and DB only if there are detections. """
    detections = current_app.latest_detections or []
    if len(detections) == 0:
        return jsonify({'saved': False, 'message': 'No defects detected; not saved.'})

    # create filename
    fname = f"capture_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.jpg"
    out_path = os.path.join(app.config['UPLOAD_FOLDER'], fname)
    # write latest_frame_jpeg bytes
    if current_app.latest_frame_jpeg is None:
        return jsonify({'saved': False, 'message': 'No frame available.'})

    with open(out_path, 'wb') as f:
        f.write(current_app.latest_frame_jpeg)

    # Save detections to DB (one row per detection)
    with app.app_context():
        for det in detections:
            new_det = Detection(
                image_filename=fname,
                crack_type=det.get('name', 'unknown'),
                confidence=det.get('confidence', 0.0),
                recommendation=current_app.latest_recommendation
            )
            db.session.add(new_det)
        db.session.commit()

    return jsonify({
        'saved': True,
        'image_url': f'/static/uploads/{fname}',
        'detections': detections,
        'message': 'Saved.'
    })

@atexit.register
def cleanup():
    global cam0, cam1, usb_cam
    if PICAMERA_AVAILABLE and is_picamera_initialized:
        try:
            cam0.stop()
            cam1.stop()
            print("CSI cameras stopped cleanly.")
        except Exception as e:
            print(f"Error stopping cameras: {e}")

    if usb_cam is not None:
        try:
            usb_cam.release()
            print("USB verification camera released cleanly.")
        except Exception as e:
            print(f"Error releasing USB camera: {e}")

with app.app_context():
    # --- Lightweight SQLite migration (adds new columns if missing) ---
    # We avoid Alembic here to keep the project simple on Raspberry Pi.
    try:
        from sqlalchemy import text

        def _sqlite_cols(table_name: str):
            rows = db.session.execute(text(f"PRAGMA table_info({table_name});")).fetchall()
            return {r[1] for r in rows}  # name is column 2

        existing = _sqlite_cols('detections')
        # If table doesn't exist yet, create_all below will handle it.
        if existing:
            add_cols = []
            if 'bogie_id' not in existing:
                add_cols.append("ALTER TABLE detections ADD COLUMN bogie_id VARCHAR(64);")
            if 'segment' not in existing:
                add_cols.append("ALTER TABLE detections ADD COLUMN segment INTEGER;")
            if 'x_local_mm' not in existing:
                add_cols.append("ALTER TABLE detections ADD COLUMN x_local_mm FLOAT;")
            if 'camera_id' not in existing:
                add_cols.append("ALTER TABLE detections ADD COLUMN camera_id INTEGER;")
            if 'bbox_cx' not in existing:
                add_cols.append("ALTER TABLE detections ADD COLUMN bbox_cx INTEGER;")
            if 'bbox_cy' not in existing:
                add_cols.append("ALTER TABLE detections ADD COLUMN bbox_cy INTEGER;")

            for stmt in add_cols:
                try:
                    db.session.execute(text(stmt))
                except Exception:
                    pass
            if add_cols:
                db.session.commit()
    except Exception:
        # Best-effort only
        pass

    db.create_all()

app.register_blueprint(main_bp)
app.register_blueprint(motor_bp)

# Expose helper for blueprint routes
app.update_bogie_status_from_usb = update_bogie_status_from_usb

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", threaded=True)
