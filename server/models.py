from typing import List, Optional

from pydantic import BaseModel, Field


class ImportPayload(BaseModel):
    week_start: str
    raw_text: str
    auto_create_project: bool = True


class LLMReportItem(BaseModel):
    project_name: str
    current_progress: str = ""
    next_plan: str = ""


class TemplateImportItem(BaseModel):
    project_name: str
    this_week_progress: List[str] = Field(default_factory=list)
    next_week_plan: List[str] = Field(default_factory=list)
    people_tagged: List[str] = Field(default_factory=list)


class LLMImportResult(BaseModel):
    items: List[LLMReportItem] = Field(default_factory=list)


class ReportBlock(BaseModel):
    index: int
    project_name: str
    matched_project_id: Optional[int] = None
    matched_project_name: Optional[str] = None
    match_score: float = 0
    current_progress: str = ""
    next_plan: str = ""
    raw_text: str = ""


class ImportResult(BaseModel):
    week_start: str
    parsed_count: int
    saved_count: int
    items: List[ReportBlock] = Field(default_factory=list)


class ProjectRow(BaseModel):
    project_id: int
    project_name: str


class WeekCell(BaseModel):
    week_start: str
    current_progress: str = ""
    next_plan: str = ""
    summary_text: str = ""


class ProjectMatrixRow(BaseModel):
    project_id: int
    project_name: str
    weeks: List[WeekCell] = Field(default_factory=list)


class DeleteWeekPayload(BaseModel):
    week_start: str


class DeleteCellPayload(BaseModel):
    project_id: int
    week_start: str


class UpdateProjectPayload(BaseModel):
    project_id: int
    project_name: str


class UpdateCellPayload(BaseModel):
    project_id: int
    week_start: str
    current_progress: str = ""
    next_plan: str = ""
