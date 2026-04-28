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


class ImportPreviewItem(BaseModel):
    index: int
    raw_project_name: str
    matched_project_id: Optional[int] = None
    matched_project_name: str = ""
    match_confidence: float = 0
    match_status: str = "new"
    current_progress: str = ""
    next_plan: str = ""
    raw_text: str = ""


class ImportPreviewResult(BaseModel):
    week_start: str
    parsed_count: int
    items: List[ImportPreviewItem] = Field(default_factory=list)


class CommitImportItem(BaseModel):
    raw_project_name: str
    project_id: Optional[int] = None
    project_name: str = ""
    current_progress: str = ""
    next_plan: str = ""
    raw_text: str = ""
    remember_alias: bool = True


class CommitImportPayload(BaseModel):
    week_start: str
    items: List[CommitImportItem] = Field(default_factory=list)


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


class MonthlyWeekItem(BaseModel):
    week_start: str
    current_progress: str = ""
    next_plan: str = ""


class MonthlyAnalysisResult(BaseModel):
    project_id: int
    project_name: str
    month: str
    month_summary: str = ""
    supplementary_actions: List[str] = Field(default_factory=list)
    next_month_plan: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)


class MonthlyProjectRow(BaseModel):
    project_id: int
    project_name: str
    month: str
    progress_digest: str = ""
    plan_digest: str = ""
    weeks: List[MonthlyWeekItem] = Field(default_factory=list)
    analysis: Optional[MonthlyAnalysisResult] = None


class MonthlyAnalysisPayload(BaseModel):
    project_id: int
    month: str


class LLMSystemSetting(BaseModel):
    config_id: Optional[int] = None
    config_name: str = ""
    provider: str = "gemini"
    model: str = "gemini-2.5-flash"
    api_key: str = ""
    base_url: str = ""
    is_active: bool = False


class SystemSettingsPayload(BaseModel):
    llm: LLMSystemSetting


class SystemSettingsResult(BaseModel):
    active_config_id: Optional[int] = None
    models: List[LLMSystemSetting] = Field(default_factory=list)
