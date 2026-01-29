import os
import cv2

class CrackDetector:
    def __init__(self, model_path: str):
        self.model = None
        self.model_path = model_path

        try:
            from ultralytics import YOLO
        except Exception as e:
            print(f"Ultralytics not available. Install dependencies. Details: {e}")
            return

        try:
            if not os.path.exists(model_path):
                print(f"Crack model not found: {model_path}")
                return

            self.model = YOLO(model_path)
            print(f"Crack model loaded successfully: {model_path}")
        except Exception as e:
            print(f"Error loading crack model ({model_path}): {e}")
            self.model = None

    def predict(self, image_path: str):
        """Predict on an image path and return a list of detections."""
        if self.model is None:
            return []

        try:
            results = self.model.predict(image_path, verbose=False)
            return self._extract_detections(results)
        except Exception as e:
            print(f"Prediction error (image): {e}")
            return []

    def predict_on_frame(self, frame_bgr):
        """
        Predict directly on a BGR frame (numpy array).
        Returns:
          detections_list: list[dict] with name/confidence/bbox
          annotated_frame: frame with boxes drawn
        """
        if self.model is None:
            return [], frame_bgr

        try:
            results = self.model.predict(source=frame_bgr, verbose=False)
            detections = self._extract_detections(results)
            annotated = results[0].plot()  # draws boxes
            return detections, annotated
        except Exception as e:
            print(f"Prediction error (frame): {e}")
            return [], frame_bgr

    @staticmethod
    def _extract_detections(results):
        """Convert Ultralytics results -> list of {name, confidence, bbox}."""
        detections = []
        if not results:
            return detections

        r = results[0]
        names = getattr(r, "names", {})

        if hasattr(r, "boxes") and r.boxes is not None and len(r.boxes) > 0:
            boxes = r.boxes

            # Robust conversion whether tensor or list
            try:
                xyxy = boxes.xyxy.cpu().numpy()
                confs = boxes.conf.cpu().numpy()
                clss = boxes.cls.cpu().numpy()
            except Exception:
                xyxy = boxes.xyxy
                confs = boxes.conf
                clss = boxes.cls

            for bb, conf, cls in zip(xyxy, confs, clss):
                x1, y1, x2, y2 = map(int, bb[:4])
                class_id = int(cls)
                name = names.get(class_id, str(class_id))
                detections.append({
                    "name": str(name),
                    "confidence": float(conf),
                    "bbox": [x1, y1, x2, y2]
                })

        return detections
