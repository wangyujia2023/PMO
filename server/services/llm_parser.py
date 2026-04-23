import json

import requests

from server.config import settings
from server.models import LLMImportResult, ReportBlock


GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

REPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "project_name": {"type": "string"},
                    "current_progress": {"type": "string"},
                    "next_plan": {"type": "string"},
                },
                "required": ["project_name", "current_progress", "next_plan"],
            },
        }
    },
    "required": ["items"],
}


def parse_weekly_report_with_gemini(raw_text: str) -> list[ReportBlock]:
    if not settings.gemini_api_key:
        raise ValueError("未配置 GEMINI_API_KEY")

    prompt = (
        "你要把项目周报文本抽取成 JSON。\n"
        "规则：\n"
        "1. 识别每个项目。\n"
        "2. project_name 只保留项目名称。\n"
        "3. current_progress 提取本周进展，没有就留空字符串。\n"
        "4. next_plan 提取下周计划/下周工作，没有就留空字符串。\n"
        "5. 不要丢失项目，不能合并项目。\n"
        "6. 输出必须严格符合 JSON Schema。\n"
        f"\n原始周报：\n{raw_text}"
    )

    response = requests.post(
        GEMINI_URL.format(model=settings.gemini_model),
        headers={
            "x-goog-api-key": settings.gemini_api_key,
            "Content-Type": "application/json",
        },
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseJsonSchema": REPORT_SCHEMA,
            },
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    text = (
        data.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [{}])[0]
        .get("text", "")
        .strip()
    )
    if not text:
        raise ValueError("Gemini 未返回结构化结果")

    parsed = LLMImportResult(**json.loads(text))
    return [
        ReportBlock(
            index=index + 1,
            project_name=item.project_name.strip(),
            current_progress=item.current_progress.strip(),
            next_plan=item.next_plan.strip(),
            raw_text="\n".join(
                [
                    item.project_name.strip(),
                    item.current_progress.strip(),
                    item.next_plan.strip(),
                ]
            ).strip(),
        )
        for index, item in enumerate(parsed.items)
        if item.project_name.strip()
    ]
