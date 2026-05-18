"""Report generator for chest X-ray analysis."""

import uuid
from datetime import datetime
from typing import List, Dict, Any

from medical_data import MEDICAL_DATA, get_severity


def generate_report(image_path: str, detections: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate a medical report from model detections.

    Args:
        image_path: Path to the analyzed image
        detections: List of detection dictionaries from model

    Returns:
        Report dictionary containing:
        - report_id: Unique report identifier
        - timestamp: Report generation time
        - image_path: Path to the analyzed image
        - detections: Enriched detection list with medical info
        - summary: Text summary of findings
        - total_findings: Number of detections
    """
    report_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().isoformat()

    enriched_detections = []
    for detection in detections:
        class_id = detection["class_id"]
        confidence = detection["confidence"]
        bbox = detection["bbox"]

        medical_info = MEDICAL_DATA.get(class_id, {})
        severity = get_severity(class_id, confidence)

        enriched_detection = {
            "class_id": class_id,
            "class_name": medical_info.get("name_en", "Unknown"),
            "class_name_cn": medical_info.get("name_cn", "未知"),
            "confidence": round(confidence, 4),
            "bbox": bbox,
            "medical_explanation": medical_info.get("explanation", ""),
            "severity": severity,
            "recommendation": medical_info.get("recommendation", "")
        }
        enriched_detections.append(enriched_detection)

    # Sort by confidence (highest first)
    enriched_detections.sort(key=lambda x: x["confidence"], reverse=True)

    # Generate summary
    total_findings = len(enriched_detections)
    if total_findings == 0:
        summary = "未发现明显异常。建议保持定期体检。"
    else:
        class_names = [d["class_name_cn"] for d in enriched_detections]
        unique_classes = list(dict.fromkeys(class_names))  # Preserve order, remove duplicates
        summary = f"检测到{total_findings}处异常，包括：{', '.join(unique_classes)}。"

    report = {
        "report_id": report_id,
        "timestamp": timestamp,
        "image_path": image_path,
        "detections": enriched_detections,
        "summary": summary,
        "total_findings": total_findings
    }

    return report
