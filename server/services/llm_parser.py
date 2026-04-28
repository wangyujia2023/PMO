import json

import requests

from server.models import LLMImportResult, LLMSystemSetting, MonthlyAnalysisResult, MonthlyProjectRow, ReportBlock


GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
OPENAI_COMPATIBLE_URL = "{base_url}/chat/completions"
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

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

MONTHLY_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "month_summary": {"type": "string"},
        "supplementary_actions": {
            "type": "array",
            "items": {"type": "string"},
        },
        "next_month_plan": {
            "type": "array",
            "items": {"type": "string"},
        },
        "risks": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["month_summary", "supplementary_actions", "next_month_plan", "risks"],
}


def _normalize_base_url(base_url: str) -> str:
    return (base_url or "").rstrip("/")


def _extract_json_text(text: str) -> str:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    return cleaned


def _request_gemini_json(prompt: str, schema: dict, llm: LLMSystemSetting) -> dict:
    if not llm.api_key:
        raise ValueError("未配置 Gemini API Key")
    response = requests.post(
        GEMINI_URL.format(model=llm.model),
        headers={
            "x-goog-api-key": llm.api_key,
            "Content-Type": "application/json",
        },
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseJsonSchema": schema,
            },
        },
        timeout=60,
    )
    if not response.ok:
        detail = response.text.strip()
        raise ValueError(f"Gemini 调用失败: {response.status_code} {detail}")
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
    return json.loads(text)


def _request_openai_compatible_json(prompt: str, schema: dict, llm: LLMSystemSetting) -> dict:
    if not llm.api_key:
        raise ValueError("未配置模型 API Key")
    base_url = _normalize_base_url(llm.base_url or (QWEN_BASE_URL if llm.provider == "qwen" else ""))
    if not base_url:
        raise ValueError("未配置模型 Base URL")
    payload = {
        "model": llm.model,
        "messages": [
            {
                "role": "system",
                "content": "你是一个只输出 JSON 的结构化助手，必须严格按照用户要求返回 JSON。",
            },
            {
                "role": "user",
                "content": (
                    f"{prompt}\n\n"
                    "输出要求：返回严格 JSON，不要带 markdown 代码块，不要输出额外解释。\n"
                    f"JSON Schema：{json.dumps(schema, ensure_ascii=False)}"
                ),
            },
        ],
        "temperature": 0.2,
    }
    if llm.provider != "qwen":
        payload["response_format"] = {"type": "json_object"}

    response = requests.post(
        OPENAI_COMPATIBLE_URL.format(base_url=base_url),
        headers={
            "Authorization": f"Bearer {llm.api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    if not response.ok:
        detail = response.text.strip()
        raise ValueError(f"模型调用失败: {response.status_code} {detail}")
    data = response.json()
    text = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    if not text:
        raise ValueError("模型未返回结构化结果")
    return json.loads(_extract_json_text(text))


def request_llm_json(prompt: str, schema: dict, llm: LLMSystemSetting) -> dict:
    provider = (llm.provider or "gemini").strip().lower()
    if provider == "gemini":
        return _request_gemini_json(prompt, schema, llm)
    if provider in {"qwen", "openai_compatible"}:
        return _request_openai_compatible_json(prompt, schema, llm)
    raise ValueError(f"暂不支持的模型提供商: {llm.provider}")


def parse_weekly_report_with_llm(raw_text: str, llm: LLMSystemSetting) -> list[ReportBlock]:
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

    parsed = LLMImportResult(**request_llm_json(prompt, REPORT_SCHEMA, llm))
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


def analyze_monthly_project_with_llm(row: MonthlyProjectRow, llm: LLMSystemSetting) -> MonthlyAnalysisResult:
    weekly_blocks = []
    for item in row.weeks:
        weekly_blocks.append(
            "\n".join(
                [
                    f"周起始日期：{item.week_start}",
                    f"本周进展：{item.current_progress or '无'}",
                    f"后续计划：{item.next_plan or '无'}",
                ]
            )
        )

    prompt = (
        "你是一名项目经营复盘助手，需要基于一个项目整月的周报内容，输出月度盘点分析 JSON。\n"
        "要求：\n"
        "1. month_summary：总结本月项目进展、关键突破、卡点与当前阶段。\n"
        "2. supplementary_actions：给出还需要补充完善的动作，要求具体、可执行。\n"
        "3. next_month_plan：给出下个月建议推进计划，要求按项目视角表述。\n"
        "4. risks：提炼当前风险、依赖项、商务/技术/采购阻塞点。\n"
        "5. 输出必须严格符合 JSON Schema。\n"
        f"\n项目名称：{row.project_name}\n"
        f"月份：{row.month}\n"
        f"本月汇总进展：\n{row.progress_digest or '无'}\n\n"
        f"本月汇总计划：\n{row.plan_digest or '无'}\n\n"
        "逐周内容：\n"
        + "\n\n".join(weekly_blocks)
    )

    parsed = request_llm_json(prompt, MONTHLY_ANALYSIS_SCHEMA, llm)
    return MonthlyAnalysisResult(
        project_id=row.project_id,
        project_name=row.project_name,
        month=row.month,
        month_summary=parsed.get("month_summary", "").strip(),
        supplementary_actions=[item.strip() for item in parsed.get("supplementary_actions", []) if item.strip()],
        next_month_plan=[item.strip() for item in parsed.get("next_month_plan", []) if item.strip()],
        risks=[item.strip() for item in parsed.get("risks", []) if item.strip()],
    )
