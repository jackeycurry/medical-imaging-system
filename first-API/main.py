"""
医学X光影像分析API - FastAPI + Ollama MedGemma1.5
"""
import io
import base64
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image
import requests

# ============== 配置 ==============
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "medgemma1.5"
API_PORT = 8008

# 默认提示词 - 要求输出病灶边界框坐标
DEFAULT_PROMPT = """请以标准放射科报告格式分析X光影像，先识别影像部位（胸部/脑部/视网膜/骨骼）。

对每一处异常病灶，在描述完影像特征后，必须在同一行输出标准边界框坐标，格式为：
[bbox] x1:y1:x2:y2:病灶标签

其中 x1,y1 是左上角坐标，x2,y2 是右下角坐标，坐标值为占图片宽高的百分比（0-100）。
多个病灶分行描述。

规则：
- 边界框坐标为0-100的百分比数值
- 每个病灶必须有独立的边界框
- 病灶标签用简短英文或拼音描述（如 feiyouqixiong右肺气胸, feizhongye结节）

只客观陈述影像所见，不做良恶性判断、不下疾病诊断、不推荐进一步检查。
结尾固定标注：本内容为人工智能辅助分析，仅供参考，不构成医疗诊断建议，需由执业医师结合临床资料综合判读。"""

# ============== FastAPI 应用 ==============
app = FastAPI(
    title="医学X光影像分析API",
    description="基于 Ollama MedGemma1.5 多模态模型的医学影像分析服务",
    version="1.0.0"
)

# 开启全局CORS跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def convert_to_jpeg_base64(image_bytes: bytes) -> str:
    """将图片转换为JPEG格式并返回Base64编码（压缩以适应Ollama）"""
    img = Image.open(io.BytesIO(image_bytes))

    # 转换为RGB模式（确保JPEG兼容）
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")

    # 转换为JPEG并编码（quality=60减小图片大小，避免超时）
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=60, optimize=True)
    jpeg_bytes = buffer.getvalue()

    return base64.b64encode(jpeg_bytes).decode("utf-8")


def call_ollama_vision(image_base64: str, prompt: str) -> str:
    """调用 Ollama 多模态模型分析图像"""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "images": [image_base64],
        "stream": False,
        "options": {
            "temperature": 0.3,
            "top_p": 0.9
        }
    }

    # 使用文件方式传输大数据，避免httpx的问题
    response = requests.post(
        f"{OLLAMA_HOST}/api/generate",
        json=payload,
        timeout=300
    )
    response.raise_for_status()
    result = response.json()
    return result.get("response", "")


def parse_bboxes(text: str) -> List[Dict[str, Any]]:
    """从响应文本中解析边界框坐标"""
    import re
    bboxes = []
    pattern = r'\[bbox\]\s*(\d+(?:\.\d+)?):(\d+(?:\.\d+)?):(\d+(?:\.\d+)?):(\d+(?:\.\d+)?):([^\s\[\]]+)'
    matches = re.findall(pattern, text)
    for match in matches:
        x1, y1, x2, y2, label = float(match[0]), float(match[1]), float(match[2]), float(match[3]), match[4]
        bboxes.append({
            "x1": round(x1, 2),
            "y1": round(y1, 2),
            "x2": round(x2, 2),
            "y2": round(y2, 2),
            "label": label
        })
    return bboxes


def draw_bboxes_on_image(
    image: Image.Image,
    bboxes: List[Dict[str, Any]]
) -> Image.Image:
    """在图片上绘制边界框标注

    Args:
        image: PIL Image对象
        bboxes: 边界框列表，每个包含 x1, y1, x2, y2, label (百分比坐标 0-100)

    Returns:
        标注后的PIL Image对象
    """
    from PIL import ImageDraw, ImageFont

    draw = ImageDraw.Draw(image)
    width, height = image.size

    # 尝试加载中文字体
    try:
        font = ImageFont.truetype("msyh.ttc", 18)
    except:
        try:
            font = ImageFont.truetype("simhei.ttf", 18)
        except:
            font = ImageFont.load_default()

    # 颜色列表，用于区分不同病灶
    colors = ["#FF0000", "#00FF00", "#FFFF00", "#00FFFF", "#FF00FF", "#FFA500", "#8000FF"]

    for i, bbox in enumerate(bboxes):
        x1_pct, y1_pct = bbox["x1"], bbox["y1"]
        x2_pct, y2_pct = bbox["x2"], bbox["y2"]

        # 将百分比坐标转换为像素坐标
        x1 = int(x1_pct * width / 100)
        y1 = int(y1_pct * height / 100)
        x2 = int(x2_pct * width / 100)
        y2 = int(y2_pct * height / 100)

        # 确保坐标在图片范围内
        x1, x2 = max(0, min(x1, width)), max(0, min(x2, width))
        y1, y2 = max(0, min(y1, height)), max(0, min(y2, height))

        # 选择颜色
        color = colors[i % len(colors)]

        # 绘制矩形框
        draw.rectangle([x1, y1, x2, y2], outline=color, width=3)

        # 绘制标签背景和文字
        label = bbox.get("label", f"lesion_{i+1}")
        label_text = f"{i+1}. {label}"

        # 获取文字边界
        text_bbox = draw.textbbox((x1, y1), label_text, font=font)
        text_w = text_bbox[2] - text_bbox[0]
        text_h = text_bbox[3] - text_bbox[1]

        # 标签背景（放在框上方或框内）
        label_y = max(y1 - text_h - 4, 0)
        draw.rectangle([x1, label_y, x1 + text_w + 4, label_y + text_h + 2], fill=color)
        draw.text((x1 + 2, label_y), label_text, fill="#000000", font=font)

    return image


@app.get("/")
async def root():
    """API信息"""
    return JSONResponse({
        "code": 200,
        "result": {
            "name": "医学X光影像分析API",
            "version": "1.0.0",
            "model": OLLAMA_MODEL,
            "endpoints": {
                "analyze": "POST /xray/analyze",
                "health": "GET /health"
            }
        }
    })


@app.get("/health")
async def health_check():
    """健康检查"""
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5.0)
        ollama_status = "online" if response.status_code == 200 else "offline"
    except Exception:
        ollama_status = "offline"

    return JSONResponse({
        "code": 200,
        "result": {
            "status": "healthy",
            "ollama": ollama_status,
            "timestamp": datetime.now().isoformat()
        }
    })


@app.post("/xray/analyze")
async def analyze_xray(
    image: UploadFile = File(..., description="X光影像图片文件"),
    prompt: Optional[str] = Form(None, description="自定义分析提示词")
):
    """
    医学X光影像分析接口

    - **image**: 上传的X光影像文件（必填，支持 JPG/PNG/WebP 等格式）
    - **prompt**: 自定义提示词（可选，不填则使用默认医学影像分析提示词）
    """
    try:
        # 1. 验证文件类型
        if not image.content_type or not image.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail="请上传有效的图片文件"
            )

        # 2. 读取图片数据
        image_bytes = await image.read()

        if len(image_bytes) == 0:
            raise HTTPException(
                status_code=400,
                detail="图片文件为空"
            )

        # 3. 转换为 JPEG Base64
        image_base64 = convert_to_jpeg_base64(image_bytes)

        # 4. 确定使用的提示词
        analysis_prompt = prompt if prompt else DEFAULT_PROMPT

        # 5. 调用 Ollama MedGemma1.5 分析
        analysis_result = call_ollama_vision(image_base64, analysis_prompt)

        if not analysis_result:
            raise HTTPException(
                status_code=500,
                detail="模型分析失败，未返回结果"
            )

        # 6. 解析边界框坐标
        bboxes = parse_bboxes(analysis_result)

        # 7. 在原图上绘制边界框
        annotated_image_base64 = None
        if bboxes:
            # 重新打开原始图片进行绘制（image对象已被读取过）
            img = Image.open(io.BytesIO(image_bytes))
            # 转换为RGB模式
            if img.mode in ("RGBA", "P", "LA"):
                img = img.convert("RGB")
            # 绘制边界框
            annotated_img = draw_bboxes_on_image(img, bboxes)
            # 转换为base64
            buffer = io.BytesIO()
            annotated_img.save(buffer, format="JPEG", quality=95)
            annotated_image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        # 8. 返回成功结果
        return JSONResponse({
            "code": 200,
            "result": {
                "analysis": analysis_result,
                "bboxes": bboxes,
                "bboxes_count": len(bboxes),
                "annotated_image": f"data:image/jpeg;base64,{annotated_image_base64}" if annotated_image_base64 else None,
                "image_type": image.content_type,
                "model": OLLAMA_MODEL,
                "prompt_used": analysis_prompt[:100] + "..." if len(analysis_prompt) > 100 else analysis_prompt,
                "timestamp": datetime.now().isoformat(),
                "report_id": str(uuid.uuid4())[:8]
            }
        })

    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "error": f"分析过程发生错误: {str(e)}"
            }
        )


# ============== 启动 ==============
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=API_PORT,
        reload=False
    )
