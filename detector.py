from ultralytics import YOLO

class CrackDetector:

    def __init__(self, model_path):

        try:
            self.model = YOLO(model_path)
            print("Model loaded successfully.")
        except Exception as e:
            print(f"Error loading model: {e}")
            self.model = None

    def predict(self, image_path):
        if self.model is None:
            print("Model is not loaded. Cannot perform prediction.")
            return []

        try:
            # Perform prediction
            results = self.model.predict(image_path, verbose=False) 
            
            # Process results
            detections = []
            result = results[0] #first image 
            class_names = result.names

            if result.boxes is not None:
                for box in result.boxes:
                    class_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    detections.append({
                        'name': class_names[class_id],
                        'confidence': round(confidence, 2)
                    })

            print("DETECTIONS:", detections)
            return detections

        except Exception as e:
            print(f"An error occurred during prediction: {e}")
            return []