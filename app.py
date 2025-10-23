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
from picamera2 import Picamera2

app = Flask(__name__, static_url_path='/static')

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(BASE_DIR, "database.db")

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)

# Global variables for Picamera2 instances
cam0 = None
cam1 = None
is_picamera_initialized = False

# Define target resolution for consistent streaming (e.g., 640x480)
# Final combined resolution will be 1280x480 (640*2 x 480)
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# --- PICAMERA2 INITIALIZATION ---
# CRITICAL FIX: Only initialize hardware in the main process when running in debug mode.
# The reloader process must be prevented from accessing the camera, otherwise it causes 'resource busy'.
if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    try:
        print("Starting Picamera2 initialization in main process...")
        # Initialize Picamera2 instances
        cam0 = Picamera2(0)
        # Configure both cameras to the same exact size for stable concatenation
        cam0.configure(cam0.create_preview_configuration({"size": (FRAME_WIDTH, FRAME_HEIGHT)})) 
        cam0.start()
        print(f"Picamera2 (index 0) initialized successfully at {FRAME_WIDTH}x{FRAME_HEIGHT}.")
        
        cam1 = Picamera2(1)
        cam1.configure(cam1.create_preview_configuration({"size": (FRAME_WIDTH, FRAME_HEIGHT)}))
        cam1.start()
        print(f"Picamera2 (index 1) initialized successfully at {FRAME_WIDTH}x{FRAME_HEIGHT}.")
        
        is_picamera_initialized = True

    except Exception as e:
        print(f"Failed to initialize Picamera2 devices: {e}")
        # Note: App continues to run, but live feed will show the placeholder
else:
    print("Picamera2 initialization skipped in reloader process.")
# --------------------------------

def generate_frames():
    """Yield frames from available cameras, or show a 'no camera' placeholder."""
    
    global cam0, cam1, is_picamera_initialized
    
    if not is_picamera_initialized:
        print("Picamera2 failed to initialize. Sending 'No camera' placeholder.")
        frame = np.zeros((FRAME_HEIGHT, FRAME_WIDTH * 2, 3), dtype=np.uint8) # Double width for two cameras
        
        # INCREASED VISIBILITY OF WARNING TEXT (BGR format for cv2)
        cv2.putText(frame, "!!! CAMERA ERROR !!!", (FRAME_WIDTH // 2 - 200, FRAME_HEIGHT // 2 - 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 3) # Big Yellow Text
        cv2.putText(frame, "DEVICE NOT FOUND OR RESOURCE BUSY.", (FRAME_WIDTH // 2 - 250, FRAME_HEIGHT // 2 + 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2) # White subtext
        
        ret, buffer = cv2.imencode('.jpg', frame)
        placeholder = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + placeholder + b'\r\n')
        return

    while True:
        frame0 = None
        frame1 = None
        
        # Capture Frame 0
        if cam0:
            try:
                frame0_rgb = cam0.capture_array()
                frame0 = cv2.cvtColor(frame0_rgb, cv2.COLOR_RGB2BGR)
                # Ensure the frame is exactly the configured size (should be already)
                if frame0.shape[0] != FRAME_HEIGHT or frame0.shape[1] != FRAME_WIDTH:
                    frame0 = cv2.resize(frame0, (FRAME_WIDTH, FRAME_HEIGHT))
            except Exception:
                # print(f"Error reading from cam0: {e}")
                frame0 = None 
                
        # Capture Frame 1
        if cam1:
            try:
                frame1_rgb = cam1.capture_array()
                frame1 = cv2.cvtColor(frame1_rgb, cv2.COLOR_RGB2BGR)
                # Ensure the frame is exactly the configured size (should be already)
                if frame1.shape[0] != FRAME_HEIGHT or frame1.shape[1] != FRAME_WIDTH:
                    frame1 = cv2.resize(frame1, (FRAME_WIDTH, FRAME_HEIGHT))
            except Exception:
                # print(f"Error reading from cam1: {e}")
                frame1 = None

        # Concatenation and Fallback Logic
        if frame0 is not None and frame1 is not None:
            # Both frames available, concatenate them horizontally
            frame = cv2.hconcat([frame0, frame1])
        elif frame0 is not None:
            # Only cam0 available
            frame = frame0
        elif frame1 is not None:
            # Only cam1 available
            frame = frame1
        else:
            # Neither camera provided a frame
            frame = None

        # Fallback if no frame was captured
        if frame is None:
            frame = np.zeros((FRAME_HEIGHT, FRAME_WIDTH * 2, 3), dtype=np.uint8)
            cv2.putText(frame, "Waiting for frames...", (FRAME_WIDTH - 150, FRAME_HEIGHT // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            time.sleep(0.1)
        
        # Encode the frame to JPEG and yield it for the stream
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        
@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# --- GRACEFUL SHUTDOWN (Cleanup Resources) ---
def release_resources():
    """Stops Picamera2 streams upon application exit."""
    print("Shutting down camera streams and releasing resources...")
    global cam0, cam1
    if cam0 and is_picamera_initialized:
        try:
            cam0.stop()
            print("Cam0 stopped.")
        except Exception as e:
            print(f"Error stopping cam0: {e}")

    if cam1 and is_picamera_initialized:
        try:
            cam1.stop()
            print("Cam1 stopped.")
        except Exception as e:
            print(f"Error stopping cam1: {e}")

# Register the cleanup function to run when the application shuts down
atexit.register(release_resources)
# ---------------------------------------------

with app.app_context():
    db.create_all()

# Register blueprint
app.register_blueprint(main_bp)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', threaded=True)
