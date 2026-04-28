from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from server.config import settings
import json

from server.models import (
    CommitImportPayload,
    DeleteCellPayload,
    DeleteWeekPayload,
    ImportPayload,
    ImportPreviewItem,
    ImportPreviewResult,
    ImportResult,
    LLMSystemSetting,
    MonthlyAnalysisPayload,
    ReportBlock,
    SystemSettingsResult,
    SystemSettingsPayload,
    TemplateImportItem,
    UpdateCellPayload,
    UpdateProjectPayload,
)
from server.schema import SCHEMA_SQL
from server.services.llm_parser import analyze_monthly_project_with_llm, parse_weekly_report_with_llm
from server.services.parser import split_blocks
from server.services.repository import ProjectRepository

app = FastAPI(title="PMO Weekly Tracker", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

repository = ProjectRepository()


@app.on_event("startup")
def startup() -> None:
    repository.init_schema(SCHEMA_SQL)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/projects")
def list_projects(keyword: str = Query(default="")):
    return repository.list_projects(keyword=keyword)


@app.get("/api/settings")
def get_settings():
    models = repository.list_llm_configs()
    active = next((item for item in models if item.is_active), None)
    return SystemSettingsResult(active_config_id=active.config_id if active else None, models=models)


@app.put("/api/settings")
def update_settings(payload: SystemSettingsPayload):
    repository.save_llm_settings(payload.llm)
    models = repository.list_llm_configs()
    active = next((item for item in models if item.is_active), None)
    return {"ok": True, "active_config_id": active.config_id if active else None, "models": models}


@app.get("/api/matrix")
def list_matrix(
    keyword: str = Query(default=""),
    week_start: str = Query(default=""),
    week_end: str = Query(default=""),
):
    return repository.list_matrix(keyword=keyword, week_start=week_start, week_end=week_end)


@app.get("/api/monthly")
def list_monthly(keyword: str = Query(default=""), month: str = Query(default="")):
    if not month:
        raise HTTPException(status_code=400, detail="缺少月份参数")
    return repository.list_monthly_review(month=month, keyword=keyword)


def parse_import_blocks(raw_text: str) -> list[ReportBlock]:
    try:
        parsed_json = json.loads(raw_text)
        template_items = [TemplateImportItem(**item) for item in parsed_json]
        return [
            ReportBlock(
                index=index + 1,
                project_name=item.project_name.strip(),
                current_progress="\n".join(item.this_week_progress).strip(),
                next_plan="\n".join(item.next_week_plan).strip(),
                raw_text=json.dumps(item.model_dump(), ensure_ascii=False, indent=2),
            )
            for index, item in enumerate(template_items)
            if item.project_name.strip()
        ]
    except Exception:
        try:
            return parse_weekly_report_with_llm(raw_text, repository.get_llm_settings())
        except Exception:
            return split_blocks(raw_text)


@app.post("/api/import/preview", response_model=ImportPreviewResult)
def preview_import(payload: ImportPayload):
    items = parse_import_blocks(payload.raw_text)
    if not items:
        raise HTTPException(status_code=400, detail="未解析到项目内容")

    preview_items = []
    catalog = repository.load_project_catalog()
    for item in items:
        matched = repository.match_project_in_catalog(item.project_name, catalog)
        preview_items.append(
            ImportPreviewItem(
                index=item.index,
                raw_project_name=item.project_name,
                matched_project_id=matched.get("project_id"),
                matched_project_name=matched.get("project_name", ""),
                match_confidence=matched.get("match_confidence", 0),
                match_status=matched.get("match_status", "new"),
                current_progress=item.current_progress,
                next_plan=item.next_plan,
                raw_text=item.raw_text,
            )
        )

    return ImportPreviewResult(week_start=payload.week_start, parsed_count=len(preview_items), items=preview_items)


@app.post("/api/import/commit", response_model=ImportResult)
def commit_import(payload: CommitImportPayload):
    saved_count = 0
    result_items: list[ReportBlock] = []
    for index, item in enumerate(payload.items):
        if item.project_id:
            project_id = item.project_id
            project_name = item.project_name or item.raw_project_name
        else:
            created = repository.ensure_project(item.project_name or item.raw_project_name)
            project_id = created["project_id"]
            project_name = created["project_name"]

        block = ReportBlock(
            index=index + 1,
            project_name=item.raw_project_name,
            matched_project_id=project_id,
            matched_project_name=project_name,
            match_score=1.0,
            current_progress=item.current_progress,
            next_plan=item.next_plan,
            raw_text=item.raw_text or item.raw_project_name,
        )
        repository.save_weekly_report(project_id, payload.week_start, block, "")
        if item.remember_alias and item.raw_project_name.strip() != project_name.strip():
            repository.save_project_alias(project_id, item.raw_project_name, "confirmed", 1.0)
        saved_count += 1
        result_items.append(block)

    return ImportResult(
        week_start=payload.week_start,
        parsed_count=len(payload.items),
        saved_count=saved_count,
        items=result_items,
    )


@app.post("/api/import", response_model=ImportResult)
def import_weekly_report(payload: ImportPayload):
    preview = preview_import(payload)
    commit_items = [
        {
            "raw_project_name": item.raw_project_name,
            "project_id": item.matched_project_id if item.match_status != "new" else None,
            "project_name": item.matched_project_name or item.raw_project_name,
            "current_progress": item.current_progress,
            "next_plan": item.next_plan,
            "raw_text": item.raw_text,
            "remember_alias": item.match_status == "auto",
        }
        for item in preview.items
    ]
    return commit_import(CommitImportPayload(week_start=payload.week_start, items=commit_items))


@app.delete("/api/week")
def delete_week(payload: DeleteWeekPayload):
    return {"deleted": repository.delete_week(payload.week_start)}


@app.delete("/api/cell")
def delete_cell(payload: DeleteCellPayload):
    return {"deleted": repository.delete_cell(payload.project_id, payload.week_start)}


@app.delete("/api/project/{project_id}")
def delete_project(project_id: int):
    return {"deleted": repository.delete_project(project_id)}


@app.patch("/api/project")
def update_project(payload: UpdateProjectPayload):
    return {"updated": repository.update_project_name(payload.project_id, payload.project_name)}


@app.patch("/api/cell")
def update_cell(payload: UpdateCellPayload):
    return {
        "updated": repository.update_cell(
            payload.project_id,
            payload.week_start,
            payload.current_progress,
            payload.next_plan,
        )
    }


@app.post("/api/monthly/analyze")
def analyze_monthly(payload: MonthlyAnalysisPayload):
    row = repository.get_monthly_project_row(payload.project_id, payload.month)
    if not row:
        raise HTTPException(status_code=404, detail="未找到项目")
    if not row.weeks:
        raise HTTPException(status_code=400, detail="该项目本月暂无周报内容")
    try:
        llm = repository.get_llm_settings()
        analysis = analyze_monthly_project_with_llm(row, llm)
        repository.save_monthly_analysis(analysis, llm)
        return analysis
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"月度分析失败: {exc}")
