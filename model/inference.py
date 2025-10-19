import json
import os

def get_latest_detections():
    # Simulated data for now
    # In production, this could read from a database, camera feed, or inference output file
    fake_data = {
        "timestamp": "2025-10-07T12:00:00",
        "bogie_id": "BFG-102",
        "detections": [
            {"type": "transverse", "confidence": 0.92, "location": [1.2, 0.5, 0.0]},
            {"type": "longitudinal", "confidence": 0.87, "location": [-0.8, 0.4, 0.1]}
        ],
        "status": "Defects detected",
        "recommendation": "Inspect weld joints and reinforce transverse beam area."
    }

    return fake_data