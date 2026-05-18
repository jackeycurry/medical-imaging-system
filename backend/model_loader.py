"""Model loader for chest X-ray analysis YOLO model."""

from ultralytics import YOLO
import os


class ChestXRayModel:
    """Singleton class for loading and running YOLO model inference."""

    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_model()
        return cls._instance

    def _load_model(self):
        """Load the YOLO model from the specified path."""
        model_path = "D:/Project/test/sec/model/best.pt"
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        self._model = YOLO(model_path)

    def predict(self, image_path: str):
        """
        Run model prediction on an image.

        Args:
            image_path: Path to the image file

        Returns:
            Ultralytics results object
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
        return self._model.predict(source=image_path, verbose=False)

    def get_detections(self, results):
        """
        Extract detections from YOLO results.

        Args:
            results: Ultralytics results object from predict()

        Returns:
            List of detection dictionaries with class_id, confidence, and bbox
        """
        detections = []
        if not results or len(results) == 0:
            return detections

        result = results[0]
        if result.boxes is None or len(result.boxes) == 0:
            return detections

        boxes = result.boxes
        for i in range(len(boxes)):
            box = boxes[i]
            detection = {
                "class_id": int(box.cls.item()),
                "confidence": float(box.conf.item()),
                "bbox": box.xyxy[0].tolist()  # [x1, y1, x2, y2]
            }
            detections.append(detection)

        return detections


# Global model instance
model_instance = ChestXRayModel()
