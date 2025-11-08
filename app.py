from flask import Flask, render_template, request, jsonify, Response
from werkzeug.utils import secure_filename
from models import db
from services.detector_service import CrackDetector
from models.detection import Detection
from routes.main_routes import main_bp
import os
import cv2
import numpy as np
import time
import atexit

# Only import picamera2 if available
try:
    from picamera2 import Picamera2
    PICAMERA_AVAILABLE = True
except ImportError:
    PICAMERA_AVAILABLE = False

app = Flask(__name__, static_url_path='/static')

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(BASE_DIR, "database.db")

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)

# Initialize YOLO detector
detector = CrackDetector("model/best.pt")

# ---------------- Camera configuration ----------------
cam0 = None
cam1 = None
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
is_picamera_initialized = False
DETECTION_ENABLED = False  # <--- NEW toggle flag

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

def generate_frames():
    """Yields concatenated frames from both cameras or a placeholder."""
    global cam0, cam1, DETECTION_ENABLED
    if not PICAMERA_AVAILABLE or not is_picamera_initialized:
        frame = np.zeros((FRAME_HEIGHT, FRAME_WIDTH * 2, 3), dtype=np.uint8)
        cv2.putText(frame, "Camera Not Available", (100, FRAME_HEIGHT // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 3)
        ret, buffer = cv2.imencode('.jpg', frame)
        yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n'
        return

    while True:
        try:
            f0 = cv2.cvtColor(cam0.capture_array(), cv2.COLOR_RGB2BGR)
            f1 = cv2.cvtColor(cam1.capture_array(), cv2.COLOR_RGB2BGR)
            frame = cv2.hconcat([f0, f1])

            # If detection is ON, run YOLO on the combined frame
            if DETECTION_ENABLED:
                frame = detector.predict_frame(frame)

        except Exception as e:
            frame = np.zeros((FRAME_HEIGHT, FRAME_WIDTH * 2, 3), dtype=np.uint8)
            cv2.putText(frame, "Waiting for frames...", (100, FRAME_HEIGHT // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

        ret, buffer = cv2.imencode('.jpg', frame)
        yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n'

@app.route("/toggle_detection", methods=["POST"])
def toggle_detection():
    """Toggle real-time crack detection."""
    global DETECTION_ENABLED
    DETECTION_ENABLED = not DETECTION_ENABLED
    return jsonify({"detection_enabled": DETECTION_ENABLED})

@app.route("/video_feed")
def video_feed():
    return Response(generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")

@atexit.register
def cleanup():
    global cam0, cam1
    if PICAMERA_AVAILABLE and is_picamera_initialized:
        try:
            cam0.stop()
            cam1.stop()
            print("Cameras stopped cleanly.")
        except Exception as e:
            print(f"Error stopping cameras: {e}")

with app.app_context():
    db.create_all()

app.register_blueprint(main_bp)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", threaded=True)
