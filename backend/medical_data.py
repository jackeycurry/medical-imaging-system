"""Medical data definitions for chest X-ray analysis."""

MEDICAL_DATA = {
    0: {
        "name_cn": "肺不张",
        "name_en": "Atelectasis",
        "explanation": "肺不张是指肺泡部分或完全塌陷，导致肺组织失去通气功能。可能由支气管阻塞、肺部感染、胸腔积液或手术後并发症引起。",
        "severity_rules": {"low": 0.4, "medium": 0.7},
        "recommendation": "建议进行胸部CT进一步评估，排除梗阻性病因。"
    },
    1: {
        "name_cn": "实变",
        "name_en": "Consolidation",
        "explanation": "肺实变是指肺泡被液体或细胞物质填充，常见于肺炎、肺水肿或肺出血。X线表现为均匀的密度增高影。",
        "severity_rules": {"low": 0.4, "medium": 0.7},
        "recommendation": "结合临床症状考虑感染性病变可能，建议抗感染治疗後复查。"
    },
    2: {
        "name_cn": "间质性肺病",
        "name_en": "ILD (Interstitial Lung Disease)",
        "explanation": "间质性肺病是一组影响肺间质的疾病，包括肺纤维化、肉芽肿性疾病等。X线表现为网格状或结节状阴影。",
        "severity_rules": {"low": 0.4, "medium": 0.7},
        "recommendation": "建议高分辨率CT检查及肺功能评估。"
    },
    3: {
        "name_cn": "浸润",
        "name_en": "Infiltration",
        "explanation": "肺部浸润通常表示肺实质存在炎症或感染过程，X线表现为模糊的密度增高影。",
        "severity_rules": {"low": 0.4, "medium": 0.7},
        "recommendation": "建议结合临床症状和实验室检查，必要时抗感染治疗。"
    },
    4: {
        "name_cn": "肺不透光",
        "name_en": "Lung Opacity",
        "explanation": "肺不透光是X线检查中发现的异常密度增高区域，可能由肺炎、肺不张、肺水肿或其他病变引起。",
        "severity_rules": {"low": 0.4, "medium": 0.7},
        "recommendation": "建议进一步CT检查以明确性质。"
    },
    5: {
        "name_cn": "结节/肿块",
        "name_en": "Nodule/Mass",
        "explanation": "肺部结节或肿块是边界清晰的圆形或卵圆形病灶。小的结节可能为良性，大的肿块需排除恶性肿瘤。",
        "severity_rules": {"low": 0.4, "medium": 0.7},
        "recommendation": "建议CT增强检查，必要时活检明确病理。"
    },
    6: {
        "name_cn": "胸腔积液",
        "name_en": "Pleural Effusion",
        "explanation": "胸腔积液是指液体异常积聚在胸膜腔内，常见于心功能不全、肝硬化、恶性肿瘤或感染。",
        "severity_rules": {"low": 0.4, "medium": 0.7},
        "recommendation": "建议超声定位穿刺抽液检查，明确积液性质。"
    },
    7: {
        "name_cn": "胸膜增厚",
        "name_en": "Pleural Thickening",
        "explanation": "胸膜增厚是指胸膜异常增厚，可能由慢性炎症、感染、石棉暴露或肿瘤引起。",
        "severity_rules": {"low": 0.4, "medium": 0.7},
        "recommendation": "建议CT评估，必要时进一步检查排除恶性病变。"
    },
    8: {
        "name_cn": "气胸",
        "name_en": "Pneumothorax",
        "explanation": "气胸是指气体进入胸膜腔导致肺组织受压塌陷，可为自发性或创伤性。严重时危及生命。",
        "severity_rules": {"low": 0.4, "medium": 0.7},
        "recommendation": "气胸为急症，需立即就医。大面积气胸需行胸腔穿刺抽气或引流。"
    },
    9: {
        "name_cn": "肺纤维化",
        "name_en": "Pulmonary Fibrosis",
        "explanation": "肺纤维化是肺组织进行性瘢痕化，导致肺功能逐渐下降。X线表现为网格状阴影和蜂窝样改变。",
        "severity_rules": {"low": 0.4, "medium": 0.7},
        "recommendation": "建议肺功能检查和高分辨率CT评估病情程度。"
    }
}


def get_severity(class_id: int, confidence: float) -> str:
    """
    Determine severity based on class_id and confidence score.

    Args:
        class_id: The class ID of the detection
        confidence: The confidence score (0-1)

    Returns:
        Severity level: 'low', 'medium', or 'high'
    """
    if class_id not in MEDICAL_DATA:
        return 'unknown'

    thresholds = MEDICAL_DATA[class_id]["severity_rules"]
    low_threshold = thresholds["low"]
    medium_threshold = thresholds["medium"]

    if confidence < low_threshold:
        return "low"
    elif confidence < medium_threshold:
        return "medium"
    else:
        return "high"


def get_medical_info(class_id: int) -> dict:
    """
    Get medical information for a specific class.

    Args:
        class_id: The class ID

    Returns:
        Dictionary with medical information or empty dict if class not found
    """
    return MEDICAL_DATA.get(class_id, {})
