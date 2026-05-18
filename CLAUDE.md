# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Medical imaging analysis and patient records management system. One main frontend + three backend services.

## Architecture

```
sec/
├── backend/                # FastAPI chest X-ray Dify integration (port 8000, secondary)
│   ├── main.py            # Dify workflow integration (secondary/legacy path)
│   ├── main_yolo.py       # Alternative: direct YOLO inference (not Dify)
│   ├── model_loader.py    # YOLO singleton (used by main_yolo only)
│   ├── medical_data.py    # 10-class definitions, severity rules
│   ├── report_generator.py  # Enriches detections with medical metadata (unused in Dify flow)
│   ├── ai_report_generator.py  # vLLM calls for AI summary (fallback on failure)
│   └── pdf_generator.py   # ReportLab PDF generation
├── yolo_api/              # ⚠ Deprecated — YOLO inference API, replaced by Qwen-VL
│   └── main.py            # Serves /detect, loads best.pt from same dir
├── medical-system-backend-fastapi/  # Main application (backend + frontend)
│   └── medical-system-backend-fastapi/
│       ├── frontend/      # ★ Active Vue 3 frontend (port 5173, Vite)
│       └── medical-system-backend-fastapi/
│           ├── main.py    # Auth, patient CRUD, records, X-ray analysis, CT analysis
│           ├── qwen_service.py  # Alibaba Cloud Qwen-VL chest X-ray analysis
│           ├── model_service.py  # ResNet50-based CT lesion detector
│           ├── models.py  # SQLAlchemy: User, Patient, MedicalRecord, MedicalImage
│           └── pdf_generator.py
├── first-API/             # Experimental Ollama MedGemma1.5 API, port 8008
│   └── main.py            # Ollama vision model with bbox parsing
├── patient_management/    # Legacy patient management system (no longer active)
│   ├── backend/           # FastAPI, SQLAlchemy, patient/exam CRUD
│   └── frontend/          # Vue 3 with router, views, stores
├── frontend/              # ⚠ Deprecated — chest X-ray only, no longer used
├── model/best.pt          # YOLO model weights (87 MB)
├── Dockerfile             # All-in-one container (backend + frontend)
├── docker-compose.yml     # Multi-service container orchestration
└── start.bat, start-all-in-one.bat, start-docker.bat, stop-*.bat
```

## Service Ports

| Service | Port | Purpose |
|---------|------|---------|
| backend/ | 8000 | Chest X-ray via Dify workflow |
| yolo_api/ | 8001 | ⚠ Deprecated — Direct YOLO detection, replaced by Qwen-VL |
| medical-system-backend-fastapi/ | 8084 (direct) / 8000 (Docker) | Main backend: auth, patients, records, images, analysis |
| medical-system frontend | 5173 | Main Vue 3 frontend (Vite dev server) |
| first-API/ | 8008 | Ollama MedGemma1.5 vision (experimental) |

Note: `main.py` hardcodes `port=8084` but the Dockerfile and docker-compose override it to 8000.

### Qwen-VL Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DASHSCOPE_API_KEY` | (required) | Alibaba Cloud DashScope API key |
| `QWEN_VL_MODEL` | `qwen3.6-flash` | Model ID for Qwen vision model |

## Data Flow (Active)

**Chest X-ray analysis** (medical-system-backend-fastapi → Alibaba Cloud Qwen-VL):
1. Frontend uploads image → `POST /api/chest-xray/analyze` (port 8084)
2. Backend encodes image as base64, calls DashScope Qwen-VL API
3. Qwen-VL returns structured JSON: `{detections, diagnosis, recommendations, patient_friendly}`
4. Maps English class names to Chinese via local `CLASS_NAME_CN`
5. Draws bounding boxes, generates PDF report
6. Returns detections + annotated image + AI report to frontend

**CT analysis** (medical-system-backend-fastapi):
- `POST /api/ct/analyze` — ResNet50 lesion detection via `model_service.py`

**Dify-based X-ray analysis** (backend/main.py, port 8000 — deprecated secondary path):
1. Image upload → Dify `/v1/files/upload` → workflow `/v1/workflows/run`
2. Parse `outputs.body` JSON for detections
3. Draw bounding boxes, generate PDF, return base64 images + report

## Running the System

```bash
# Prerequisite: set Alibaba Cloud API key
set DASHSCOPE_API_KEY=sk-your-api-key

# Option 1: Windows launcher (Backend + Frontend)
.\start.bat                    # Runs python main.py directly, backend on port 8084

# Option 2: Docker Compose (separate containers)
.\start-docker.bat             # docker-compose up -d --build
# Or: docker-compose up -d

# Option 3: All-in-one Docker container
.\start-all-in-one.bat         # Single container (backend + frontend)
# Or: docker build -t medical-system . && docker run -d -e DASHSCOPE_API_KEY=%DASHSCOPE_API_KEY% -p 8000:8000 -p 5173:5173 medical-system

# Option 4: Manual (individual components)
cd medical-system-backend-fastapi/medical-system-backend-fastapi/medical-system-backend-fastapi && python main.py  # port 8084
cd medical-system-backend-fastapi/medical-system-backend-fastapi/frontend && npm install && npm run dev  # port 5173
```

## Key Implementation Details

### Dify Integration (backend/main.py)
- `DIFY_BASE_URL`: `http://localhost/v1`
- API key hardcoded in `main.py`
- `parse_dify_result()` extracts detections from `outputs.body` JSON
- `CLASS_NAME_CN` in main.py maps 13 English→Chinese names
- `model_loader.py` and `report_generator.py` are NOT used in the Dify flow — they are for the alternative `main_yolo.py` path

### CLASS_NAME_CN Mappings
Three separate mappings exist — keep them consistent when adding classes:
- `backend/main.py`: 13 classes (Dify return values)
- `backend/pdf_generator.py`: 3 classes (subset for display)
- `medical-system-backend-fastapi/.../main.py`: 14 classes (YOLO direct return)

### vLLM Integration (ai_report_generator.py)
- Calls `localhost:8001/v1/chat/completions` with Qwen2.5-7B model
- Falls back to `_generate_fallback_report()` on failure
- System prompt instructs model to return JSON with `diagnosis`, `recommendations`, `patient_friendly`

### YOLO API (yolo_api/main.py)
- Patches `torch.load` for weights_only=False compatibility
- Loads `best.pt` on startup, supports CUDA
- Single endpoint: `POST /detect` — returns `{image_size, detections}`
- Called by medical-system-backend at `http://localhost:8001/detect`

### Database
- `medical-system-backend-fastapi/` uses SQLAlchemy with SQLite (`medical_system.db`)
- `patient_management/` uses SQLAlchemy with SQLite (`patient_management.db`)
- Default admin: `admin / 123456` (created at startup)

### Qwen-VL Service (qwen_service.py)
- Calls Alibaba Cloud DashScope API (`dashscope.aliyuncs.com/compatible-mode/v1/chat/completions`)
- Encodes chest X-ray images as base64 data URLs for multimodal input
- System prompt instructs model to detect 14 abnormality classes and return structured JSON with bbox coords (0-1000 normalized)
- Response parser handles: markdown-wrapped JSON, raw JSON, plain text fallback, malformed JSON
- Model configurable via `QWEN_VL_MODEL` env var (default: `qwen3.6-flash`)
- Replaces three previous components: yolo_api, Dify workflow, and vLLM report generation

### Hardcoded Paths
- Model: `D:/Project/test/sec/model/best.pt` (model_loader.py) and `best.pt` relative (yolo_api)
- Uploads: `D:/Project/test/sec/backend/uploads`
- Reports: `D:/Project/test/sec/backend/reports`
- Chinese fonts: system fonts (msyh.ttc, simhei.ttf, simhei.ttf)

### Tests
There is no test suite in this codebase. A manual test script exists at `medical-system-backend-fastapi/medical-system-backend-fastapi/medical-system-backend-fastapi/test_api.py` (basic requests-based smoke test).

### Git Notes
- `main` is the merge target branch
- `model/best.pt` is large (87 MB) — ensure it's gitignored unless tracked intentionally

### Directory Nesting Note
The path `medical-system-backend-fastapi/medical-system-backend-fastapi/medical-system-backend-fastapi/` is not a typo — the directory is nested three levels deep. The intermediate level (`medical-system-backend-fastapi/medical-system-backend-fastapi/`) also contains the `frontend/` directory.
