from . import db
from datetime import datetime
from models import db

class Detection(db.Model):
    __tablename__ = 'detections'

    id = db.Column(db.Integer, primary_key=True)
    image_filename = db.Column(db.String(255), nullable=False)
    crack_type = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(100), nullable=True)
    confidence = db.Column(db.Float, nullable=False)
    # Mapping fields (mm). We treat scene units as millimeters.
    # gantry_x: global X position along bogie length (0..1900)
    # gantry_y: left/right position across bogie width (approx, Phase 1)
    gantry_x = db.Column(db.Float, nullable=True)
    gantry_y = db.Column(db.Float, nullable=True)
    # Scan/run metadata
    bogie_id = db.Column(db.String(64), nullable=True, index=True)
    segment = db.Column(db.Integer, nullable=True)  # 1 or 2
    x_local_mm = db.Column(db.Float, nullable=True)  # 0..950 from motor
    camera_id = db.Column(db.Integer, nullable=True)  # 0=left(CSI0), 1=right(CSI1)
    bbox_cx = db.Column(db.Integer, nullable=True)
    bbox_cy = db.Column(db.Integer, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    recommendation = db.Column(db.String(500), nullable=True)

    def __repr__(self):
        return f"<Detection {self.id} - {self.crack_type}>"