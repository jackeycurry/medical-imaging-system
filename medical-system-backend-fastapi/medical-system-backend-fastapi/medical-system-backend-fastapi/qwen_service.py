"""
Chest X-ray analysis via Alibaba Cloud DashScope Qwen-VL model.
Replaces the previous YOLO + Dify pipeline with a single VLM call.
"""
import os
import json
import re
import base64
from pathlib import Path

import httpx

# Configuration
DASHSCOPE_API_KEY = os.environ.get(
    "DASHSCOPE_API_KEY",
    "sk-b4b4d850280740e59e17bcfd1807271f"
)
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_MODEL = os.environ.get("QWEN_VL_MODEL", "qwen3.6-flash")

# English → Chinese class name mapping (for keyword extraction from Chinese reports)
CN_KEYWORD_MAP = {
    "主动脉增宽": "Aortic enlargement",
    "主动脉": "Aortic enlargement",
    "肺不张": "Atelectasis",
    "钙化": "Calcification",
    "钙化灶": "Calcification",
    "心脏增大": "Cardiomegaly",
    "心影增大": "Cardiomegaly",
    "锁骨骨折": "Clavicle fracture",
    "实变": "Consolidation",
    "弥漫性结节": "Diffuse nodular opacities",
    "结节影": "Diffuse nodular opacities",
    "胸腔积液": "Effusion",
    "积液": "Effusion",
    "肺气肿": "Emphysema",
    "肺动脉增宽": "Enlarged PA",
    "间质性肺病": "ILD",
    "间质": "ILD",
    "浸润": "Infiltration",
    "肺透光度": "Lung Opacity",
    "结节": "Nodule/Mass",
    "肿块": "Nodule/Mass",
    "气胸": "Pneumothorax",
    "胸膜增厚": "Pleural Thickening",
    "肺纤维化": "Pulmonary Fibrosis",
}

SYSTEM_PROMPT = """你是一位资深胸部影像学专家，请严格按照以下规范生成结构化分析报告，仅做影像特征描述，不做临床诊断。

## 分析流程
1. 影像质量评估（体位、曝光、伪影、完整度）
2. 逐解剖区域扫描：肺野→胸膜→纵隔→心脏→膈肌→骨骼→软组织
3. 对每处异常单独标注，宁可多报不可漏报（低至0.5置信度也标出）
4. 汇总形成影像学印象，按严重程度排序

## bbox 标注规范（关键）
- bbox 必须紧贴病灶实际边缘，仅框选异常组织本身，避免纳入大量正常组织
- 不确定边界时宁可稍紧，也不要画大框
- 小病灶（<50px）用紧凑小框，大病灶（>200px）精确勾画轮廓
- 每个病灶独立标注，不要合并多个不相邻的病灶
- bbox 采用 0-1000 归一化坐标，格式 [x1, y1, x2, y2]

class_name 严格限定以下 14 类：
"Aortic enlargement", "Atelectasis", "Calcification", "Cardiomegaly", "Clavicle fracture", "Consolidation", "Diffuse nodular opacities", "Effusion", "Emphysema", "Enlarged PA", "ILD", "Infiltration", "Lung Opacity", "Nodule/Mass"

## 输出 JSON（详细结构化报告）
{
  "quality_assessment": "影像质量评估：体位是否正、曝光是否合适、有无伪影、图像完整度",
  "anatomical_findings": {
    "lung_fields": "双肺野：透亮度、纹理、有无渗出/实变/结节/空洞/纤维化",
    "pleura": "胸膜：有无增厚、粘连、钙化、积液/气胸征象",
    "mediastinum": "纵隔：宽度、有无占位/淋巴结肿大/移位",
    "heart": "心脏：大小、形态、心胸比、有无增大征象",
    "diaphragm": "膈肌：位置、形态、肋膈角是否锐利",
    "bones": "骨骼：肋骨、锁骨、胸椎有无骨折/破坏/畸形",
    "soft_tissue": "软组织：胸壁、颈部有无异常密度/钙化/异物"
  },
  "detections": [
    {
      "class_name": "异常类型",
      "confidence": 0.85,
      "bbox": [x1, y1, x2, y2],
      "description": "该病灶的影像特征简述（大小、形态、密度、边缘等）"
    }
  ],
  "diagnosis": "汇总：逐条列出所有阳性发现+重要阴性发现，每条一行",
  "impression": "影像学印象：按优先级排序的关键结论（≤5条），最可疑/最紧急的排最前",
  "recommendations": "建议：①随访建议（含时间间隔）②进一步检查建议（CT/MRI/超声等）③临床关注要点",
  "patient_friendly": "用通俗语言向患者说明检查结果，避免恐吓性词汇，强调配合医生进一步诊疗"
}

完全正常时 detections 为 []，各 anatomical_findings 填"未见明显异常"。
只输出 JSON，不要任何额外文字或 markdown 标记。"""

CT_SYSTEM_PROMPT = """你是一位资深胸部影像学专家，请对这张胸部CT影像进行逐层、逐区域的结构化分析。仅做影像特征描述，不做临床诊断。

## 分析流程
1. 影像质量与扫描参数评估（层厚、窗宽窗位、伪影、扫描范围完整度）
2. 按解剖分区逐层扫描：胸壁软组织→骨骼→纵隔→心脏大血管→气管支气管→双肺野→胸膜→膈肌
3. 对每处异常单独标注（低至0.5置信度也可标出），宁可多报不可漏报
4. 区分阳性发现与阴性正常结果，阴性结果同样重要
5. 按严重程度/紧急程度排序形成印象

## bbox 标注规范
- bbox 紧贴病灶实际边缘，仅框选异常组织本身
- 每个病灶独立标注 bbox
- bbox 采用 0-1000 归一化坐标，格式 [x1, y1, x2, y2]

## 检测类别（14类，但CT中常见有差异）
"Aortic enlargement", "Atelectasis", "Calcification", "Cardiomegaly", "Clavicle fracture", "Consolidation", "Diffuse nodular opacities", "Effusion", "Emphysema", "Enlarged PA", "ILD", "Infiltration", "Lung Opacity", "Nodule/Mass"

CT中还需关注：纵隔气肿、皮下气肿、淋巴结肿大、空洞、支气管扩张、磨玻璃影、网格影等（可在class_name中使用上述14类最接近的类别，description中补充CT特征细节）

## 输出 JSON（项目演示用详细报告）
{
  "quality_assessment": "影像质量评估（含扫描参数观察）",
  "anatomical_findings": {
    "soft_tissue": "胸壁软组织及颈部：皮下气肿/水肿/肿块/异物等",
    "bones": "骨骼：肋骨/胸椎/锁骨/胸骨有无骨折/破坏/转移",
    "mediastinum": "纵隔：宽度/气肿/占位/淋巴结/移位",
    "heart_vessels": "心脏及大血管：大小/形态/钙化/夹层",
    "airways": "气管及支气管：通畅度/管壁/异物",
    "lung_fields": "双肺野：透亮度/纹理/结节/实变/GGO/空洞/纤维化",
    "pleura": "胸膜及胸腔：积液/气胸/增厚/钙化",
    "diaphragm": "膈肌：位置/形态"
  },
  "detections": [
    {
      "class_name": "异常类型（严格从14类中选）",
      "confidence": 0.85,
      "bbox": [x1, y1, x2, y2],
      "description": "该病灶的CT影像特征（大小/形态/密度/边缘/增强特点）",
      "term_explanation": "用通俗语言解释这个医学术语的含义，让非医学背景人士也能理解",
      "clinical_significance": "客观说明此发现的可能原因、临床关注点、常见关联疾病（纯客观，不做诊断结论）"
    }
  ],
  "diagnosis": "汇总：阳性发现逐条列出 + 重要阴性发现（如：双肺未见实变、双侧未见积液）",
  "impression": "影像学印象：按优先级排序（最紧急排最前），每条简明扼要",
  "recommendations": "建议：①随访建议（含时间）②进一步检查（CT增强/MRI/PET-CT等）③临床关注要点",
  "patient_friendly": "通俗说明，非医学背景人士可理解，不含恐吓性词汇"
}

**重要：** term_explanation 和 clinical_significance 字段必须填写，这是项目演示用途的关键内容。
完全正常时 detections 为 []。
只输出 JSON，不要任何额外文字或 markdown 标记。"""


def _encode_image(image_path: str | Path) -> str:
    path = Path(image_path)
    ext = path.suffix.lower()
    mime_map = {".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png", ".bmp": "bmp", ".webp": "webp"}
    mime = mime_map.get(ext, "jpeg")
    with open(path, "rb") as f:
        return f"data:image/{mime};base64,{base64.b64encode(f.read()).decode('utf-8')}"


def _extract_json(text: str) -> dict | None:
    """Try multiple strategies to extract valid JSON from VLM response."""
    # Strategy 1: JSON in markdown code block
    for pattern in [r'```(?:json)?\s*\n?(.*?)\n?```', r'```(?:json)?\s*(.*?)\s*```']:
        m = re.search(pattern, text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1).strip())
            except json.JSONDecodeError:
                pass

    # Strategy 2: Direct JSON parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 3: Find balanced JSON object
    for match in re.finditer(r'\{', text):
        depth = 0
        start = match.start()
        for i, ch in enumerate(text[start:], start):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        break
    return None


def _extract_detections_from_text(text: str) -> list:
    """Extract abnormality detections from Chinese medical text by keyword matching."""
    detections = []
    seen = set()
    for cn_keyword, en_name in CN_KEYWORD_MAP.items():
        if cn_keyword in text and en_name not in seen:
            detections.append({
                "class_name": en_name,
                "confidence": 0.7,  # inferred from text, not model-scored
                "bbox": [0, 0, 1000, 1000],
                "bbox_approximate": True  # text-extracted, no precise coords available
            })
            seen.add(en_name)
    return detections


def _parse_vlm_response(text: str) -> dict:
    """Parse Qwen-VL response to extract detections and diagnostic report.

    Handles:
    1. Expected format: {detections, diagnosis, recommendations, patient_friendly}
    2. Alternative format: {detection_results, diagnostic_report}
    3. Plain text fallback with keyword extraction
    """
    data = _extract_json(text)

    if data is None:
        # No JSON found — use whole text as diagnosis, extract keywords
        detections = _extract_detections_from_text(text)
        return {
            "detections": detections,
            "diagnosis": text.strip() or "模型未返回有效的诊断结果",
            "recommendations": "建议由专业医生复核",
            "patient_friendly": "请咨询医生获取详细解读",
            "impression": "",
            "quality_assessment": "无法评估（模型未返回结构化数据）",
            "anatomical_findings": {}
        }

    # Check which format the model used
    if "detections" in data and isinstance(data["detections"], list):
        # Expected format — validate detections
        valid_dets = []
        for det in data["detections"]:
            if not isinstance(det, dict):
                continue
            bbox = det.get("bbox", [0, 0, 1000, 1000])
            if not isinstance(bbox, list) or len(bbox) != 4:
                bbox = [0, 0, 1000, 1000]
            bbox = [max(0, min(1000, int(v))) for v in bbox]
            det_entry = {
                "class_name": str(det.get("class_name", "unknown")),
                "confidence": round(float(det.get("confidence", 0.7)), 4),
                "bbox": bbox
            }
            if det.get("description"):
                det_entry["description"] = str(det["description"])
            valid_dets.append(det_entry)

        # Extract anatomical_findings
        anatomical = data.get("anatomical_findings", {})
        if not isinstance(anatomical, dict):
            anatomical = {}

        return {
            "detections": valid_dets,
            "diagnosis": str(data.get("diagnosis", "")).strip(),
            "recommendations": str(data.get("recommendations", "")).strip(),
            "patient_friendly": str(data.get("patient_friendly", "")).strip(),
            "impression": str(data.get("impression", "")).strip(),
            "quality_assessment": str(data.get("quality_assessment", "")).strip(),
            "anatomical_findings": anatomical,
        }

    # Alternative format: {detection_results, diagnostic_report} or similar
    report = data.get("diagnostic_report", {})
    detection_results = data.get("detection_results", {})

    # Build diagnosis from findings + impression
    findings = ""
    if isinstance(detection_results, dict):
        findings = "；".join(f"{k}: {v}" for k, v in detection_results.items() if v)

    impression_text = ""
    if isinstance(report, dict):
        impression = report.get("impression", [])
        if isinstance(impression, list):
            impression_text = "；".join(impression)
        elif isinstance(impression, str):
            impression_text = impression

        diagnosis_parts = []
        if report.get("findings"):
            diagnosis_parts.append(f"影像所见：{report['findings']}")
        if impression_text:
            diagnosis_parts.append(f"诊断印象：{impression_text}")
        diagnosis = "\n".join(diagnosis_parts)

        recommendation = report.get("recommendation", "")
    else:
        diagnosis = findings or str(report)
        recommendation = ""

    # Extract detections from the impression/keywords
    combined_text = f"{findings} {impression_text} {diagnosis}"
    detections = _extract_detections_from_text(combined_text)

    # Also try top-level keys
    if not detections:
        flat_text = json.dumps(data, ensure_ascii=False)
        detections = _extract_detections_from_text(flat_text)

    return {
        "detections": detections,
        "diagnosis": diagnosis or str(data),
        "recommendations": recommendation or "建议由专业医生复核",
        "patient_friendly": impression_text or "请咨询医生获取详细解读",
        "impression": impression_text,
        "quality_assessment": "",
        "anatomical_findings": {},
    }


async def analyze_chest_xray(image_path: str | Path, symptoms_text: str = "") -> dict:
    """Analyze chest X-ray image using Qwen-VL model.

    Args:
        image_path: Path to the chest X-ray image
        symptoms_text: Optional formatted symptom descriptions for context

    Returns:
        {
            "detections": [{class_name, confidence, bbox}, ...],
            "diagnosis": str,
            "recommendations": str,
            "patient_friendly": str,
        }
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    image_data_url = _encode_image(image_path)

    user_text = "请分析这张胸部X光片，严格按JSON格式返回结果。"
    if symptoms_text:
        user_text += f"\n\n患者症状信息（请结合症状进行影像分析）：{symptoms_text}"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": image_data_url}},
                {"type": "text", "text": user_text}
            ]
        }
    ]

    async with httpx.AsyncClient(timeout=120.0, trust_env=False) as client:
        response = await client.post(
            f"{DASHSCOPE_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": QWEN_MODEL,
                "messages": messages,
                "temperature": 0,
                "max_tokens": 4096,
            }
        )

    if response.status_code != 200:
        error_detail = response.text[:500]
        print(f"[QWEN] API error {response.status_code}: {error_detail}")
        raise RuntimeError(f"Qwen-VL API 调用失败 (HTTP {response.status_code})")

    result = response.json()
    choices = result.get("choices", [])
    if not choices:
        raise RuntimeError("Qwen-VL 未返回有效结果")

    content = choices[0].get("message", {}).get("content", "")
    print(f"[QWEN] Raw response length: {len(content)} chars")
    print(f"[QWEN] Raw response (first 1500 chars): {content[:1500]}")

    parsed = _parse_vlm_response(content)
    print(f"[QWEN] Parsed: {len(parsed['detections'])} detections, "
          f"diagnosis length: {len(parsed['diagnosis'])} chars, "
          f"detection names: {[d['class_name'] for d in parsed['detections']]}")

    return parsed


async def analyze_ct_image(image_path: str | Path, symptoms_text: str = "") -> dict:
    """Analyze chest CT image using Qwen-VL model with CT-specific prompt.

    Returns structured dict with term_explanation and clinical_significance
    for each detection, suitable for generating a project demo report.
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    image_data_url = _encode_image(image_path)

    user_text = "请分析这张胸部CT影像，逐区域扫描，严格按JSON格式返回详细结果。每条发现的术语解释和临床意义字段必须填写。"
    if symptoms_text:
        user_text += f"\n\n患者症状信息（请结合症状进行影像分析）：{symptoms_text}"

    messages = [
        {"role": "system", "content": CT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": image_data_url}},
                {"type": "text", "text": user_text}
            ]
        }
    ]

    async with httpx.AsyncClient(timeout=180.0, trust_env=False) as client:
        response = await client.post(
            f"{DASHSCOPE_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": QWEN_MODEL,
                "messages": messages,
                "temperature": 0,
                "max_tokens": 4096,
            }
        )

    if response.status_code != 200:
        error_detail = response.text[:500]
        print(f"[QWEN-CT] API error {response.status_code}: {error_detail}")
        raise RuntimeError(f"Qwen-VL API 调用失败 (HTTP {response.status_code})")

    result = response.json()
    choices = result.get("choices", [])
    if not choices:
        raise RuntimeError("Qwen-VL 未返回有效结果")

    content = choices[0].get("message", {}).get("content", "")
    print(f"[QWEN-CT] Raw response length: {len(content)} chars")

    parsed = _parse_vlm_response(content)
    print(f"[QWEN-CT] Parsed: {len(parsed['detections'])} detections")

    # _parse_vlm_response handles generic parsing; ensure term_explanation
    # and clinical_significance are preserved from the raw JSON
    raw_data = _extract_json(content)
    if raw_data and "detections" in raw_data:
        raw_dets = raw_data.get("detections", [])
        for i, det in enumerate(parsed.get("detections", [])):
            if i < len(raw_dets) and isinstance(raw_dets[i], dict):
                if raw_dets[i].get("term_explanation"):
                    det["term_explanation"] = str(raw_dets[i]["term_explanation"])
                if raw_dets[i].get("clinical_significance"):
                    det["clinical_significance"] = str(raw_dets[i]["clinical_significance"])

    return parsed


# ========== Brain / 脑部检测 ==========

BRAIN_SYSTEM_PROMPT = """你是一位资深神经影像学专家，请对这张脑部影像（CT/MRI）进行结构化分析，仅做影像特征描述，不做临床诊断。

## 分析流程
1. 影像质量评估（扫描参数、运动伪影、对比度、图像完整度）
2. 逐解剖分区扫描：颅骨→硬膜外/硬膜下间隙→蛛网膜下腔→脑实质（灰质/白质/深部核团）→脑室系统→中线结构→血管→蝶鞍区
3. 对每处异常单独标注，宁可多报不可漏报（低至0.5置信度也标出）
4. 汇总形成影像学印象，按严重程度/紧急程度排序

## bbox 标注规范
- bbox 紧贴病灶实际边缘，仅框选异常组织本身
- 每个病灶独立标注 bbox，不要合并多个不相邻的病灶
- bbox 采用 0-1000 归一化坐标，格式 [x1, y1, x2, y2]

class_name 严格限定以下 14 类：
"Brain hemorrhage", "Brain infarction", "Brain tumor", "Brain atrophy", "Hydrocephalus", "Skull fracture", "Brain edema", "Midline shift", "Subdural hematoma", "Epidural hematoma", "Subarachnoid hemorrhage", "White matter lesions", "Aneurysm", "Vascular malformation"

## 输出 JSON（详细结构化报告）
{
  "quality_assessment": "影像质量评估：扫描方式（CT/MRI平扫/增强）、有无运动伪影、图像完整度",
  "anatomical_findings": {
    "skull": "颅骨：有无骨折、骨质破坏、畸形、术后改变",
    "extra_axial": "硬膜外/硬膜下/蛛网膜下腔：有无血肿、积液、积脓",
    "brain_parenchyma": "脑实质：灰白质分界、有无出血/梗死/占位/水肿/萎缩",
    "ventricles": "脑室系统：大小、形态、对称性、有无积水、占位效应",
    "midline": "中线结构：有无移位（方向及程度）",
    "vessels": "血管：有无动脉瘤、血管畸形、狭窄/闭塞征象",
    "sella": "蝶鞍区：鞍区有无占位/空蝶鞍"
  },
  "detections": [
    {
      "class_name": "异常类型（严格从14类中选）",
      "confidence": 0.85,
      "bbox": [x1, y1, x2, y2],
      "description": "该病灶的影像特征简述（位置、大小、形态、密度/信号特点、占位效应等）",
      "term_explanation": "用通俗语言解释这个医学术语的含义",
      "clinical_significance": "客观说明此发现的可能原因、临床关注点、常见关联疾病"
    }
  ],
  "diagnosis": "汇总：逐条列出所有阳性发现+重要阴性发现，每条一行",
  "impression": "影像学印象：按优先级排序的关键结论（≤5条），最紧急排最前",
  "recommendations": "建议：①急诊/观察建议 ②进一步检查（MRI增强/MRA/DSA/CTP等）③临床关注要点",
  "patient_friendly": "用通俗语言向患者说明检查结果，避免恐吓性词汇，强调配合医生进一步诊疗"
}

完全正常时 detections 为 []，各 anatomical_findings 填"未见明显异常"。
只输出 JSON，不要任何额外文字或 markdown 标记。"""


async def analyze_brain_image(image_path: str | Path, symptoms_text: str = "") -> dict:
    """Analyze brain CT/MRI image using Qwen-VL model."""
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    image_data_url = _encode_image(image_path)

    user_text = "请分析这张脑部影像，逐区域扫描，严格按JSON格式返回详细结果。每条发现的术语解释和临床意义字段必须填写。"
    if symptoms_text:
        user_text += f"\n\n患者症状信息（请结合症状进行影像分析）：{symptoms_text}"

    messages = [
        {"role": "system", "content": BRAIN_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": image_data_url}},
                {"type": "text", "text": user_text}
            ]
        }
    ]

    async with httpx.AsyncClient(timeout=180.0, trust_env=False) as client:
        response = await client.post(
            f"{DASHSCOPE_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": QWEN_MODEL,
                "messages": messages,
                "temperature": 0,
                "max_tokens": 4096,
            }
        )

    if response.status_code != 200:
        error_detail = response.text[:500]
        print(f"[QWEN-BRAIN] API error {response.status_code}: {error_detail}")
        raise RuntimeError(f"Qwen-VL API 调用失败 (HTTP {response.status_code})")

    result = response.json()
    choices = result.get("choices", [])
    if not choices:
        raise RuntimeError("Qwen-VL 未返回有效结果")

    content = choices[0].get("message", {}).get("content", "")
    print(f"[QWEN-BRAIN] Raw response length: {len(content)} chars")

    parsed = _parse_vlm_response(content)
    print(f"[QWEN-BRAIN] Parsed: {len(parsed['detections'])} detections")

    raw_data = _extract_json(content)
    if raw_data and "detections" in raw_data:
        raw_dets = raw_data.get("detections", [])
        for i, det in enumerate(parsed.get("detections", [])):
            if i < len(raw_dets) and isinstance(raw_dets[i], dict):
                if raw_dets[i].get("term_explanation"):
                    det["term_explanation"] = str(raw_dets[i]["term_explanation"])
                if raw_dets[i].get("clinical_significance"):
                    det["clinical_significance"] = str(raw_dets[i]["clinical_significance"])

    return parsed


# ========== Retina / 视网膜检测 ==========

RETINA_SYSTEM_PROMPT = """你是一位资深眼底病学专家，请对这张眼底照片（视网膜摄像）进行结构化分析，仅做影像特征描述，不做临床诊断。

## 分析流程
1. 影像质量评估（对焦清晰度、曝光、视野范围、有无睫毛/眼睑遮挡伪影）
2. 逐一解剖结构扫描：视盘→黄斑→视网膜血管→后极部视网膜→周边视网膜→玻璃体
3. 对每处异常单独标注，宁可多报不可漏报（低至0.5置信度也标出）
4. 汇总形成影像学印象，按严重程度排序

## bbox 标注规范
- bbox 紧贴病灶实际边缘，仅框选异常区域本身
- 每个病灶独立标注 bbox，不要合并不相邻的病灶
- bbox 采用 0-1000 归一化坐标，格式 [x1, y1, x2, y2]

class_name 严格限定以下 14 类：
"Diabetic retinopathy", "Macular degeneration", "Glaucoma suspect", "Retinal hemorrhage", "Retinal detachment", "Papilledema", "Arteriosclerosis", "Microaneurysm", "Cotton wool spots", "Hard exudates", "Drusen", "Venous beading", "Macular edema", "Retinal vein occlusion"

## 输出 JSON（详细结构化报告）
{
  "quality_assessment": "影像质量评估：对焦是否清晰、曝光是否合适、视野范围、有无伪影",
  "anatomical_findings": {
    "optic_disc": "视盘：边缘是否清晰、颜色、杯盘比、有无水肿/苍白/凹陷/新生血管",
    "macula": "黄斑：中心凹反光、有无水肿/渗出/出血/脱离/变性/裂孔",
    "retinal_vessels": "视网膜血管：管径、走行、动脉硬化征象（铜丝/银丝样）、有无串珠/白鞘/闭塞/新生血管",
    "posterior_pole": "后极部视网膜：有无出血/渗出/微动脉瘤/棉絮斑/水肿",
    "peripheral_retina": "周边视网膜：有无变性/裂孔/脱离/出血/色素改变",
    "vitreous": "玻璃体：有无混浊/出血/星状小体/后脱离"
  },
  "detections": [
    {
      "class_name": "异常类型（严格从14类中选）",
      "confidence": 0.85,
      "bbox": [x1, y1, x2, y2],
      "description": "该病灶的影像特征简述（位置、大小、形态、颜色/反光特点、深度/层次）",
      "term_explanation": "用通俗语言解释这个医学术语的含义",
      "clinical_significance": "客观说明此发现的可能原因、临床关注点、常见关联疾病"
    }
  ],
  "diagnosis": "汇总：逐条列出所有阳性发现+重要阴性发现，每条一行",
  "impression": "影像学印象：按优先级排序的关键结论（≤5条），最紧急排最前",
  "recommendations": "建议：①随访建议（含时间间隔）②进一步检查（OCT/FFA/眼压/视野等）③临床关注要点",
  "patient_friendly": "用通俗语言向患者说明检查结果，避免恐吓性词汇，强调配合医生进一步诊疗"
}

完全正常时 detections 为 []，各 anatomical_findings 填"未见明显异常"。
只输出 JSON，不要任何额外文字或 markdown 标记。"""


async def analyze_retina_image(image_path: str | Path, symptoms_text: str = "") -> dict:
    """Analyze retinal fundus image using Qwen-VL model."""
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    image_data_url = _encode_image(image_path)

    user_text = "请分析这张眼底照片，逐结构扫描，严格按JSON格式返回详细结果。每条发现的术语解释和临床意义字段必须填写。"
    if symptoms_text:
        user_text += f"\n\n患者症状信息（请结合症状进行影像分析）：{symptoms_text}"

    messages = [
        {"role": "system", "content": RETINA_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": image_data_url}},
                {"type": "text", "text": user_text}
            ]
        }
    ]

    async with httpx.AsyncClient(timeout=180.0, trust_env=False) as client:
        response = await client.post(
            f"{DASHSCOPE_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": QWEN_MODEL,
                "messages": messages,
                "temperature": 0,
                "max_tokens": 4096,
            }
        )

    if response.status_code != 200:
        error_detail = response.text[:500]
        print(f"[QWEN-RETINA] API error {response.status_code}: {error_detail}")
        raise RuntimeError(f"Qwen-VL API 调用失败 (HTTP {response.status_code})")

    result = response.json()
    choices = result.get("choices", [])
    if not choices:
        raise RuntimeError("Qwen-VL 未返回有效结果")

    content = choices[0].get("message", {}).get("content", "")
    print(f"[QWEN-RETINA] Raw response length: {len(content)} chars")

    parsed = _parse_vlm_response(content)
    print(f"[QWEN-RETINA] Parsed: {len(parsed['detections'])} detections")

    raw_data = _extract_json(content)
    if raw_data and "detections" in raw_data:
        raw_dets = raw_data.get("detections", [])
        for i, det in enumerate(parsed.get("detections", [])):
            if i < len(raw_dets) and isinstance(raw_dets[i], dict):
                if raw_dets[i].get("term_explanation"):
                    det["term_explanation"] = str(raw_dets[i]["term_explanation"])
                if raw_dets[i].get("clinical_significance"):
                    det["clinical_significance"] = str(raw_dets[i]["clinical_significance"])

    return parsed


# ========== Abdomen / 腹部检测 ==========

ABDOMEN_SYSTEM_PROMPT = """你是一位资深腹部影像学专家，请对这张腹部影像（CT/MRI/超声）进行结构化分析，仅做影像特征描述，不做临床诊断。

## 分析流程
1. 影像质量评估（扫描方式、层厚、对比度、呼吸伪影、完整度）
2. 逐一解剖分区扫描：肝脏→胆囊及胆道→胰腺→脾脏→双肾及肾上腺→胃肠道→腹膜腔→血管→淋巴结→腹壁
3. 对每处异常单独标注，宁可多报不可漏报（低至0.5置信度也标出）
4. 汇总形成影像学印象，按严重程度排序

## bbox 标注规范
- bbox 紧贴病灶实际边缘，仅框选异常组织本身
- 每个病灶独立标注 bbox，不要合并多个不相邻的病灶
- bbox 采用 0-1000 归一化坐标，格式 [x1, y1, x2, y2]

class_name 严格限定以下 14 类：
"Liver lesion", "Gallbladder stone", "Bile duct dilation", "Pancreatic mass", "Splenomegaly", "Renal cyst", "Renal stone", "Hydronephrosis", "Adrenal mass", "Ascites", "Abdominal lymphadenopathy", "Bowel obstruction", "Abdominal aortic aneurysm", "Peritoneal thickening"

## 输出 JSON（详细结构化报告）
{
  "quality_assessment": "影像质量评估：扫描方式/序列、有无呼吸伪影、图像完整度",
  "anatomical_findings": {
    "liver": "肝脏：大小、形态、密度/信号、有无占位/囊肿/钙化/脂肪浸润",
    "gallbladder_biliary": "胆囊及胆道：胆囊大小、壁厚、有无结石/息肉、胆管有无扩张",
    "pancreas": "胰腺：大小、形态、密度/信号、有无占位/囊肿/钙化、胰管有无扩张",
    "spleen": "脾脏：大小、形态、密度/信号、有无占位/梗死",
    "kidneys_adrenals": "双肾及肾上腺：大小、形态、实质厚度、有无结石/囊肿/积水/占位",
    "gi_tract": "胃肠道：有无梗阻/扩张/占位/炎症征象",
    "peritoneum": "腹膜腔：有无积液/积气/增厚/种植",
    "vessels": "腹部血管：腹主动脉、下腔静脉有无扩张/夹层/血栓/狭窄",
    "lymph_nodes": "淋巴结：有无肿大（位置、大小、形态）",
    "abdominal_wall": "腹壁：有无异常密度/疝/肿块"
  },
  "detections": [
    {
      "class_name": "异常类型（严格从14类中选）",
      "confidence": 0.85,
      "bbox": [x1, y1, x2, y2],
      "description": "该病灶的影像特征简述（位置、大小、形态、密度/信号、边缘等）",
      "term_explanation": "用通俗语言解释这个医学术语的含义",
      "clinical_significance": "客观说明此发现的可能原因、临床关注点、常见关联疾病"
    }
  ],
  "diagnosis": "汇总：逐条列出所有阳性发现+重要阴性发现，每条一行",
  "impression": "影像学印象：按优先级排序的关键结论（≤5条），最紧急排最前",
  "recommendations": "建议：①随访建议（含时间间隔）②进一步检查（增强CT/MRI/超声/内镜等）③临床关注要点",
  "patient_friendly": "用通俗语言向患者说明检查结果，避免恐吓性词汇，强调配合医生进一步诊疗"
}

完全正常时 detections 为 []，各 anatomical_findings 填"未见明显异常"。
只输出 JSON，不要任何额外文字或 markdown 标记。"""


async def analyze_abdomen_image(image_path: str | Path, symptoms_text: str = "") -> dict:
    """Analyze abdominal CT/MRI/ultrasound image using Qwen-VL model."""
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    image_data_url = _encode_image(image_path)

    user_text = "请分析这张腹部影像，逐区域扫描，严格按JSON格式返回详细结果。每条发现的术语解释和临床意义字段必须填写。"
    if symptoms_text:
        user_text += f"\n\n患者症状信息（请结合症状进行影像分析）：{symptoms_text}"

    messages = [
        {"role": "system", "content": ABDOMEN_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": image_data_url}},
                {"type": "text", "text": user_text}
            ]
        }
    ]

    async with httpx.AsyncClient(timeout=180.0, trust_env=False) as client:
        response = await client.post(
            f"{DASHSCOPE_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": QWEN_MODEL,
                "messages": messages,
                "temperature": 0,
                "max_tokens": 4096,
            }
        )

    if response.status_code != 200:
        error_detail = response.text[:500]
        print(f"[QWEN-ABDOMEN] API error {response.status_code}: {error_detail}")
        raise RuntimeError(f"Qwen-VL API 调用失败 (HTTP {response.status_code})")

    result = response.json()
    choices = result.get("choices", [])
    if not choices:
        raise RuntimeError("Qwen-VL 未返回有效结果")

    content = choices[0].get("message", {}).get("content", "")
    print(f"[QWEN-ABDOMEN] Raw response length: {len(content)} chars")

    parsed = _parse_vlm_response(content)
    print(f"[QWEN-ABDOMEN] Parsed: {len(parsed['detections'])} detections")

    raw_data = _extract_json(content)
    if raw_data and "detections" in raw_data:
        raw_dets = raw_data.get("detections", [])
        for i, det in enumerate(parsed.get("detections", [])):
            if i < len(raw_dets) and isinstance(raw_dets[i], dict):
                if raw_dets[i].get("term_explanation"):
                    det["term_explanation"] = str(raw_dets[i]["term_explanation"])
                if raw_dets[i].get("clinical_significance"):
                    det["clinical_significance"] = str(raw_dets[i]["clinical_significance"])

    return parsed


# ========== Spine / 脊柱检测 ==========

SPINE_SYSTEM_PROMPT = """你是一位资深骨肌影像学专家，请对这张脊柱影像（X光/CT/MRI）进行结构化分析，仅做影像特征描述，不做临床诊断。

## 分析流程
1. 影像质量评估（投照位置、扫描范围、伪影、图像完整度）
2. 逐解剖结构扫描：脊柱曲度→椎体序列→各椎体形态→椎间盘→椎管→小关节→韧带→周围软组织
3. 对每处异常单独标注，宁可多报不可漏报（低至0.5置信度也标出）
4. 汇总形成影像学印象，按严重程度/紧急程度排序

## bbox 标注规范
- bbox 紧贴病灶实际边缘，仅框选异常组织本身
- 每个病灶独立标注 bbox，不要合并多个不相邻的病灶
- bbox 采用 0-1000 归一化坐标，格式 [x1, y1, x2, y2]

class_name 严格限定以下 14 类：
"Vertebral compression fracture", "Disc herniation", "Spinal stenosis", "Scoliosis", "Spondylolisthesis", "Osteophyte formation", "Schmorl node", "Vertebral hemangioma", "Bone metastasis", "Ankylosing spondylitis", "Spinal tuberculosis", "Ligament ossification", "Disc degeneration", "Spina bifida"

## 输出 JSON（详细结构化报告）
{
  "quality_assessment": "影像质量评估：投照/扫描方式、体位、有无伪影、图像完整度",
  "anatomical_findings": {
    "spinal_curvature": "脊柱曲度：生理曲度是否正常，有无侧弯/后凸/前凸异常",
    "vertebral_alignment": "椎体序列：有无滑脱、不稳、阶梯状改变",
    "vertebral_body": "各椎体：高度、形态、骨质密度、有无骨折/破坏/畸形/血管瘤",
    "intervertebral_disc": "椎间盘：高度、信号/密度、有无突出/膨出/脱出/钙化",
    "spinal_canal": "椎管：前后径、有无狭窄、有无占位",
    "facet_joints": "小关节：有无增生/退变/半脱位/积液",
    "ligaments": "韧带：有无肥厚/骨化（后纵韧带、黄韧带）",
    "soft_tissue": "周围软组织：有无肿胀/肿块/脓肿"
  },
  "detections": [
    {
      "class_name": "异常类型（严格从14类中选）",
      "confidence": 0.85,
      "bbox": [x1, y1, x2, y2],
      "description": "该病灶的影像特征简述（位置/节段、大小、形态、密度/信号特点）",
      "term_explanation": "用通俗语言解释这个医学术语的含义",
      "clinical_significance": "客观说明此发现的可能原因、临床关注点、常见关联疾病"
    }
  ],
  "diagnosis": "汇总：逐条列出所有阳性发现+重要阴性发现，每条一行",
  "impression": "影像学印象：按优先级排序的关键结论（≤5条），最紧急排最前",
  "recommendations": "建议：①随访建议（含时间间隔）②进一步检查（CT/MRI/骨扫描等）③临床关注要点",
  "patient_friendly": "用通俗语言向患者说明检查结果，避免恐吓性词汇，强调配合医生进一步诊疗"
}

完全正常时 detections 为 []，各 anatomical_findings 填"未见明显异常"。
只输出 JSON，不要任何额外文字或 markdown 标记。"""


async def analyze_spine_image(image_path: str | Path, symptoms_text: str = "") -> dict:
    """Analyze spine X-ray/CT/MRI image using Qwen-VL model."""
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    image_data_url = _encode_image(image_path)

    user_text = "请分析这张脊柱影像，逐结构扫描，严格按JSON格式返回详细结果。每条发现的术语解释和临床意义字段必须填写。"
    if symptoms_text:
        user_text += f"\n\n患者症状信息（请结合症状进行影像分析）：{symptoms_text}"

    messages = [
        {"role": "system", "content": SPINE_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": image_data_url}},
                {"type": "text", "text": user_text}
            ]
        }
    ]

    async with httpx.AsyncClient(timeout=180.0, trust_env=False) as client:
        response = await client.post(
            f"{DASHSCOPE_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": QWEN_MODEL,
                "messages": messages,
                "temperature": 0,
                "max_tokens": 4096,
            }
        )

    if response.status_code != 200:
        error_detail = response.text[:500]
        print(f"[QWEN-SPINE] API error {response.status_code}: {error_detail}")
        raise RuntimeError(f"Qwen-VL API 调用失败 (HTTP {response.status_code})")

    result = response.json()
    choices = result.get("choices", [])
    if not choices:
        raise RuntimeError("Qwen-VL 未返回有效结果")

    content = choices[0].get("message", {}).get("content", "")
    print(f"[QWEN-SPINE] Raw response length: {len(content)} chars")

    parsed = _parse_vlm_response(content)
    print(f"[QWEN-SPINE] Parsed: {len(parsed['detections'])} detections")

    raw_data = _extract_json(content)
    if raw_data and "detections" in raw_data:
        raw_dets = raw_data.get("detections", [])
        for i, det in enumerate(parsed.get("detections", [])):
            if i < len(raw_dets) and isinstance(raw_dets[i], dict):
                if raw_dets[i].get("term_explanation"):
                    det["term_explanation"] = str(raw_dets[i]["term_explanation"])
                if raw_dets[i].get("clinical_significance"):
                    det["clinical_significance"] = str(raw_dets[i]["clinical_significance"])

    return parsed


# ========== Breast / 乳腺检测 ==========

BREAST_SYSTEM_PROMPT = """你是一位资深乳腺影像学专家，请对这张乳腺影像（钼靶/超声/MRI）进行结构化分析，仅做影像特征描述，不做临床诊断。

## 分析流程
1. 影像质量评估（投照位置、压迫程度、伪影、图像完整度）
2. 逐一解剖结构扫描：皮肤→皮下脂肪→乳腺实质→乳晕后区→胸肌→腋窝
3. 对每处异常单独标注（低至0.5置信度也标出），并评估BI-RADS分级倾向
4. 汇总形成影像学印象，按严重程度排序

## bbox 标注规范
- bbox 紧贴病灶实际边缘，仅框选异常组织本身
- 每个病灶独立标注 bbox，不要合并多个不相邻的病灶
- bbox 采用 0-1000 归一化坐标，格式 [x1, y1, x2, y2]

class_name 严格限定以下 14 类：
"Breast mass", "Microcalcification", "Architectural distortion", "Asymmetry", "Skin thickening", "Nipple retraction", "Axillary lymphadenopathy", "Breast cyst", "Fibroadenoma", "Ductal ectasia", "Intramammary lymph node", "Fat necrosis", "Focal asymmetry", "Breast edema"

## 输出 JSON（详细结构化报告）
{
  "quality_assessment": "影像质量评估：投照位置/方式、压迫程度、有无伪影、图像完整度",
  "anatomical_findings": {
    "skin": "皮肤：厚度、有无凹陷/增厚/橘皮样改变",
    "subcutaneous_fat": "皮下脂肪：层次是否清晰、有无异常密度/占位",
    "breast_parenchyma": "乳腺实质：腺体类型（脂肪型/散在纤维腺体型/不均匀致密型/极度致密型）、有无肿块/钙化/结构扭曲",
    "retroareolar": "乳晕后区：有无肿块/导管扩张/钙化",
    "pectoral_muscle": "胸肌：有无受侵/异常密度",
    "axilla": "腋窝：有无淋巴结肿大（大小、形态、皮质厚度、有无脂肪门）"
  },
  "detections": [
    {
      "class_name": "异常类型（严格从14类中选）",
      "confidence": 0.85,
      "bbox": [x1, y1, x2, y2],
      "description": "该病灶的影像特征简述（位置/象限、大小、形态、边缘、密度/回声、钙化形态）",
      "term_explanation": "用通俗语言解释这个医学术语的含义",
      "clinical_significance": "客观说明此发现的可能原因、临床关注点、常见关联疾病"
    }
  ],
  "diagnosis": "汇总：逐条列出所有阳性发现+重要阴性发现，每条一行",
  "impression": "影像学印象：按优先级排序的关键结论（≤5条），最紧急排最前，附BI-RADS评估倾向",
  "recommendations": "建议：①随访建议（含时间间隔）②进一步检查（超声/钼靶加摄/MRI/穿刺活检等）③临床关注要点",
  "patient_friendly": "用通俗语言向患者说明检查结果，避免恐吓性词汇，强调配合医生进一步诊疗"
}

完全正常时 detections 为 []，各 anatomical_findings 填"未见明显异常"。
只输出 JSON，不要任何额外文字或 markdown 标记。"""


async def analyze_breast_image(image_path: str | Path, symptoms_text: str = "") -> dict:
    """Analyze breast mammography/ultrasound/MRI image using Qwen-VL model."""
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    image_data_url = _encode_image(image_path)

    user_text = "请分析这张乳腺影像，逐结构扫描，严格按JSON格式返回详细结果。每条发现的术语解释和临床意义字段必须填写。"
    if symptoms_text:
        user_text += f"\n\n患者症状信息（请结合症状进行影像分析）：{symptoms_text}"

    messages = [
        {"role": "system", "content": BREAST_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": image_data_url}},
                {"type": "text", "text": user_text}
            ]
        }
    ]

    async with httpx.AsyncClient(timeout=180.0, trust_env=False) as client:
        response = await client.post(
            f"{DASHSCOPE_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": QWEN_MODEL,
                "messages": messages,
                "temperature": 0,
                "max_tokens": 4096,
            }
        )

    if response.status_code != 200:
        error_detail = response.text[:500]
        print(f"[QWEN-BREAST] API error {response.status_code}: {error_detail}")
        raise RuntimeError(f"Qwen-VL API 调用失败 (HTTP {response.status_code})")

    result = response.json()
    choices = result.get("choices", [])
    if not choices:
        raise RuntimeError("Qwen-VL 未返回有效结果")

    content = choices[0].get("message", {}).get("content", "")
    print(f"[QWEN-BREAST] Raw response length: {len(content)} chars")

    parsed = _parse_vlm_response(content)
    print(f"[QWEN-BREAST] Parsed: {len(parsed['detections'])} detections")

    raw_data = _extract_json(content)
    if raw_data and "detections" in raw_data:
        raw_dets = raw_data.get("detections", [])
        for i, det in enumerate(parsed.get("detections", [])):
            if i < len(raw_dets) and isinstance(raw_dets[i], dict):
                if raw_dets[i].get("term_explanation"):
                    det["term_explanation"] = str(raw_dets[i]["term_explanation"])
                if raw_dets[i].get("clinical_significance"):
                    det["clinical_significance"] = str(raw_dets[i]["clinical_significance"])

    return parsed


# ========== Cardiovascular / 心血管检测 ==========

CARDIOVASCULAR_SYSTEM_PROMPT = """你是一位资深心血管影像学专家，请对这张心血管影像（CTA/MRA/超声/造影）进行结构化分析，仅做影像特征描述，不做临床诊断。

## 分析流程
1. 影像质量评估（扫描方式/序列、对比剂充盈程度、伪影、图像完整度）
2. 逐一解剖结构扫描：冠状动脉→心脏各腔室→心脏瓣膜→心肌→心包→主动脉→肺动脉→外周血管
3. 对每处异常单独标注，宁可多报不可漏报（低至0.5置信度也标出）
4. 汇总形成影像学印象，按严重程度/紧急程度排序

## bbox 标注规范
- bbox 紧贴病灶实际边缘，仅框选异常组织本身
- 每个病灶独立标注 bbox，不要合并多个不相邻的病灶
- bbox 采用 0-1000 归一化坐标，格式 [x1, y1, x2, y2]

class_name 严格限定以下 14 类：
"Coronary artery stenosis", "Coronary calcification", "Aortic dissection", "Aortic stenosis", "Mitral regurgitation", "Left ventricular hypertrophy", "Cardiac thrombus", "Pericardial effusion", "Pulmonary embolism", "Deep vein thrombosis", "Carotid artery plaque", "Ventricular aneurysm", "Atrial septal defect", "Aortic valve calcification"

## 输出 JSON（详细结构化报告）
{
  "quality_assessment": "影像质量评估：扫描方式、对比剂充盈程度、伪影、图像完整度",
  "anatomical_findings": {
    "coronary_arteries": "冠状动脉：起源、走行、有无狭窄/钙化/斑块/夹层/扩张",
    "cardiac_chambers": "各腔室：大小、形态、室壁厚度、有无占位/血栓",
    "heart_valves": "心脏瓣膜：开放/关闭情况、有无狭窄/反流/钙化/赘生物",
    "myocardium": "心肌：厚度、有无肥厚/变薄/梗死/纤维化/运动异常",
    "pericardium": "心包：有无增厚/积液/钙化/缩窄",
    "aorta": "主动脉：管径、管壁、有无夹层/动脉瘤/溃疡/壁间血肿",
    "pulmonary_vessels": "肺血管：有无栓塞/狭窄/动静脉瘘",
    "peripheral_vessels": "外周血管：颈动脉/下肢血管有无斑块/狭窄/闭塞/血栓"
  },
  "detections": [
    {
      "class_name": "异常类型（严格从14类中选）",
      "confidence": 0.85,
      "bbox": [x1, y1, x2, y2],
      "description": "该病灶的影像特征简述（位置/节段、长度/范围、程度、形态特点）",
      "term_explanation": "用通俗语言解释这个医学术语的含义",
      "clinical_significance": "客观说明此发现的可能原因、临床关注点、常见关联疾病"
    }
  ],
  "diagnosis": "汇总：逐条列出所有阳性发现+重要阴性发现，每条一行",
  "impression": "影像学印象：按优先级排序的关键结论（≤5条），最紧急排最前",
  "recommendations": "建议：①急诊/观察建议 ②进一步检查（冠脉造影/心超/CTA/MRA等）③临床关注要点",
  "patient_friendly": "用通俗语言向患者说明检查结果，避免恐吓性词汇，强调配合医生进一步诊疗"
}

完全正常时 detections 为 []，各 anatomical_findings 填"未见明显异常"。
只输出 JSON，不要任何额外文字或 markdown 标记。"""


async def analyze_cardiovascular_image(image_path: str | Path, symptoms_text: str = "") -> dict:
    """Analyze cardiovascular CTA/MRA/ultrasound image using Qwen-VL model."""
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    image_data_url = _encode_image(image_path)

    user_text = "请分析这张心血管影像，逐结构扫描，严格按JSON格式返回详细结果。每条发现的术语解释和临床意义字段必须填写。"
    if symptoms_text:
        user_text += f"\n\n患者症状信息（请结合症状进行影像分析）：{symptoms_text}"

    messages = [
        {"role": "system", "content": CARDIOVASCULAR_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": image_data_url}},
                {"type": "text", "text": user_text}
            ]
        }
    ]

    async with httpx.AsyncClient(timeout=180.0, trust_env=False) as client:
        response = await client.post(
            f"{DASHSCOPE_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": QWEN_MODEL,
                "messages": messages,
                "temperature": 0,
                "max_tokens": 4096,
            }
        )

    if response.status_code != 200:
        error_detail = response.text[:500]
        print(f"[QWEN-CARDIO] API error {response.status_code}: {error_detail}")
        raise RuntimeError(f"Qwen-VL API 调用失败 (HTTP {response.status_code})")

    result = response.json()
    choices = result.get("choices", [])
    if not choices:
        raise RuntimeError("Qwen-VL 未返回有效结果")

    content = choices[0].get("message", {}).get("content", "")
    print(f"[QWEN-CARDIO] Raw response length: {len(content)} chars")

    parsed = _parse_vlm_response(content)
    print(f"[QWEN-CARDIO] Parsed: {len(parsed['detections'])} detections")

    raw_data = _extract_json(content)
    if raw_data and "detections" in raw_data:
        raw_dets = raw_data.get("detections", [])
        for i, det in enumerate(parsed.get("detections", [])):
            if i < len(raw_dets) and isinstance(raw_dets[i], dict):
                if raw_dets[i].get("term_explanation"):
                    det["term_explanation"] = str(raw_dets[i]["term_explanation"])
                if raw_dets[i].get("clinical_significance"):
                    det["clinical_significance"] = str(raw_dets[i]["clinical_significance"])

    return parsed
