from . import db
from datetime import datetime
from models import db
# from models.detection import Detection

class Detection(db.Model):
    __tablename__ = 'detections'

    id = db.Column(db.Integer, primary_key=True)
    image_filename = db.Column(db.String(255), nullable=False)
    crack_type = db.Column(db.String(100), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    gantry_x = db.Column(db.Float, nullable=True)
    gantry_y = db.Column(db.Float, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    recommendation = db.Column(db.String(500), nullable=True)

    def __repr__(self):
        return f"<Detection {self.id} - {self.crack_type}>"