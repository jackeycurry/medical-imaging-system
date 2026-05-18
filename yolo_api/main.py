import io
import functools
from contextlib import asynccontextmanager
from pathlib import Path

import torch
import torch.serialization
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image

torch.serialization.add_safe_globals(["ultralytics.nn.tasks.DetectionModel"])

_original_torch_load = torch.load


@functools.wraps(_original_torch_load)
def _patched_torch_load(*args, **kwargs):
    kwargs.setdefault("weights_only", False)
    return _original_torch_load(*args, **kwargs)


torch.load = _patched_torch_load

from ultralytics import YOLO


MODEL_PATH = Path(__file__).parent / "best.pt"
model = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    if not MODEL_PATH.exists():
        raise RuntimeError(f"Model not found: {MODEL_PATH}")
    model = YOLO(str(MODEL_PATH))
    if torch.cuda.is_available():
        model.to("cuda")
    print(f"YOLO model loaded, device: {'cuda' if torch.cuda.is_available() else 'cpu'}")
    yield
    model = None


app = FastAPI(title="YOLO Detection API", lifespan=lifespan)


@app.post("/detect")
async def detect(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "Only image files are supported")

    contents = await file.read()
    img = Image.open(io.BytesIO(contents)).convert("RGB")

    results = model.predict(img, verbose=False)
    result = results[0]

    boxes = []
    for box in result.boxes:
        boxes.append({
            "class_id": int(box.cls.item()),
            "class_name": result.names[int(box.cls.item())],
            "confidence": round(float(box.conf.item()), 4),
            "bbox": [round(x, 2) for x in box.xyxy[0].tolist()],
        })

    return JSONResponse({
        "image_size": result.orig_shape,
        "detections": boxes,
    })


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": model is not None}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
