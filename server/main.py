from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from server.config import settings
import json

from server.models import (
    DeleteCellPayload,
    DeleteWeekPayload,
    ImportPayload,
    ImportResult,
    ReportBlock,
    TemplateImportItem,
    UpdateCellPayload,
    UpdateProjectPayload,
)
from server.schema import SCHEMA_SQL
from server.services.llm_parser import parse_weekly_report_with_gemini
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


@app.get("/api/matrix")
def list_matrix(
    keyword: str = Query(default=""),
    week_start: str = Query(default=""),
    week_end: str = Query(default=""),
):
    return repository.list_matrix(keyword=keyword, week_start=week_start, week_end=week_end)


@app.post("/api/import", response_model=ImportResult)
def import_weekly_report(payload: ImportPayload):
    parsed_from_template = False
    try:
        parsed_json = json.loads(payload.raw_text)
        template_items = [TemplateImportItem(**item) for item in parsed_json]
        items = [
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
        parsed_from_template = True
    except Exception:
        try:
            items = parse_weekly_report_with_gemini(payload.raw_text)
        except Exception:
            items = split_blocks(payload.raw_text)
    if not items:
        raise HTTPException(status_code=400, detail="未解析到项目内容")

    saved_count = 0
    if parsed_from_template:
        project_map = repository.load_project_name_map()
        for item in items:
            project_name = item.project_name.strip()
            matched = project_map.get(project_name)
            if matched:
                item.matched_project_id = matched["project_id"]
                item.matched_project_name = matched["project_name"]
                item.match_score = 1.0
            elif payload.auto_create_project:
                created = repository.ensure_project(project_name)
                item.matched_project_id = created["project_id"]
                item.matched_project_name = created["project_name"]
                item.match_score = 1.0
                project_map[project_name] = created

            if item.matched_project_id:
                repository.save_weekly_report(item.matched_project_id, payload.week_start, item, "")
                saved_count += 1
    else:
        for item in items:
            matched = repository.find_best_project(item.project_name)
            if matched and matched["score"] >= 0.72:
                item.matched_project_id = matched["project_id"]
                item.matched_project_name = matched["project_name"]
                item.match_score = matched["score"]
            elif payload.auto_create_project:
                created = repository.ensure_project(item.project_name)
                item.matched_project_id = created["project_id"]
                item.matched_project_name = created["project_name"]
                item.match_score = created["score"]

            if item.matched_project_id:
                repository.save_weekly_report(item.matched_project_id, payload.week_start, item, "")
                saved_count += 1

    return ImportResult(
        week_start=payload.week_start,
        parsed_count=len(items),
        saved_count=saved_count,
        items=items,
    )


@app.delete("/api/week")
def delete_week(payload: DeleteWeekPayload):
    return {"deleted": repository.delete_week(payload.week_start)}


@app.delete("/api/cell")
def delete_cell(payload: DeleteCellPayload):
    return {"deleted": repository.delete_cell(payload.project_id, payload.week_start)}


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
