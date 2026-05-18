"""AI报告生成器 - 调用vLLM生成详细医学分析报告"""

import requests
from typing import Dict, Any, Optional

VLLM_API_URL = "http://localhost:8001/v1/chat/completions"
MODEL_NAME = "/mnt/d/models/Qwen2.5-7B-Instruct-AWQ"

SYSTEM_PROMPT = """你是一位资深放射科医生，正在与患者进行诊断结果沟通。请用温暖、专业、易懂的语言为患者解读胸部X光检测结果。

请严格按照以下JSON格式输出（不要添加其他内容）：
{
    "diagnosis": "诊断分析（以医生口吻解读，专业但亲切，200-500字）",
    "recommendations": "临床建议（具体、可操作的检查和治疗建议，100-300字）",
    "patient_friendly": "通俗说明（用打比方的方式解释，让非医学专业患者也能理解，100-200字）"
}

语气要求：
1. 诊断分析：像医生在诊室里对患者说话，既专业又让人安心
2. 临床建议：具体明确，让患者知道下一步该怎么做
3. 通俗说明：用生活化的比喻解释医学发现，不要让患者感到害怕"""

USER_PROMPT_TEMPLATE = """这是一份患者的胸部X光检测报告，请为患者生成一份通俗易懂的诊断报告。

检测到{count}处需要关注的异常：
{detections}

请用温暖专业的医生口吻，像在诊室里与患者沟通一样，生成诊断报告。请严格按照JSON格式输出，不要添加其他内容。"""


def generate_ai_report(detections: list) -> Dict[str, Any]:
    """
    调用vLLM生成AI分析报告

    Args:
        detections: YOLO检测结果列表
        image_description: 图像描述（可选）

    Returns:
        包含diagnosis, recommendations, patient_friendly的字典
    """
    if not detections:
        return {
            "diagnosis": "未检测到明显异常。胸部X光片未见显著异常改变。",
            "recommendations": "建议保持定期体检，继续关注呼吸系统健康。",
            "patient_friendly": "您的胸部X光检查结果正常，未发现明显异常。请继续保持健康的生活方式。"
        }

    # 构建检测结果描述
    detection_texts = []
    for i, det in enumerate(detections, 1):
        detection_texts.append(
            f"{i}. {det.get('class_name_cn', '未知')} ({det.get('class_name', 'Unknown')})，"
            f"置信度{det.get('confidence', 0) * 100:.1f}%，"
            f"严重程度: {det.get('severity', 'unknown')}"
        )

    detections_str = "\n".join(detection_texts)
    count = len(detections)

    user_prompt = USER_PROMPT_TEMPLATE.format(
        count=count,
        detections=detections_str
    )

    try:
        response = requests.post(
            VLLM_API_URL,
            headers={"Content-Type": "application/json"},
            json={
                "model": MODEL_NAME,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 1500
            },
            timeout=60
        )
        response.raise_for_status()

        # 处理响应编码
        response_encoding = response.encoding or 'utf-8'
        result = response.json()
        content = result["choices"][0]["message"]["content"].strip()

        # 尝试修复编码问题
        if isinstance(content, bytes):
            content = content.decode('utf-8', errors='replace')
        elif response_encoding.lower() not in ('utf-8', 'utf8'):
            try:
                content = content.encode(response_encoding).decode('utf-8')
            except (UnicodeDecodeError, UnicodeEncodeError):
                content = content.encode('latin-1').decode('utf-8', errors='replace')

        # 尝试解析JSON
        import json
        # 尝试提取JSON部分（可能在```json块中）
        if content.startswith("```"):
            lines = content.split("\n")
            json_start = -1
            json_end = -1
            for i, line in enumerate(lines):
                if "```json" in line or "```" in line:
                    if json_start == -1:
                        json_start = i + 1
                    else:
                        json_end = i
                        break
            if json_start > 0 and json_end > 0:
                content = "\n".join(lines[json_start:json_end])

        return json.loads(content)

    except Exception as e:
        # 如果调用失败，返回默认报告
        print(f"vLLM调用失败: {e}")
        return _generate_fallback_report(detections)


def _generate_fallback_report(detections: list) -> Dict[str, Any]:
    """生成备用报告（当vLLM调用失败时）"""
    detection_names = [d.get('class_name_cn', '未知') for d in detections]
    unique_names = list(dict.fromkeys(detection_names))

    return {
        "diagnosis": f"检测到{len(detections)}处异常，包括：{', '.join(unique_names)}。具体情况需结合临床症状进一步评估。",
        "recommendations": "建议：根据检测结果，建议进一步进行CT检查以明确病变性质，并咨询呼吸科或胸外科专科医生。",
        "patient_friendly": f"检查发现以下异常：{', '.join(unique_names)}。这些发现需要医生进一步评估。建议您尽快就医咨询专业医生。"
    }
