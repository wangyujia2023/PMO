import json
from datetime import date
from typing import Any, Dict, List, Optional

from server.config import settings
from server.database import get_cursor, get_server_connection
from server.models import LLMSystemSetting, MonthlyAnalysisResult, MonthlyProjectRow, MonthlyWeekItem, ProjectMatrixRow, ProjectRow, ReportBlock, WeekCell
from server.services.matcher import normalize_name, score_project_name


class ProjectRepository:
    def ensure_llm_model_configs_table(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS llm_model_configs (
            config_id BIGINT NOT NULL AUTO_INCREMENT,
            config_name VARCHAR(100) NOT NULL,
            provider VARCHAR(50) NOT NULL,
            model VARCHAR(100) NOT NULL,
            api_key LONGTEXT NULL,
            base_url VARCHAR(500) NULL,
            is_active TINYINT(1) NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (config_id),
            UNIQUE KEY uk_config_name (config_name),
            KEY idx_is_active (is_active)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        with get_cursor() as cursor:
            cursor.execute(sql)

    def ensure_monthly_analysis_table(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS monthly_project_analyses (
            analysis_id BIGINT NOT NULL AUTO_INCREMENT,
            project_id BIGINT NOT NULL,
            month CHAR(7) NOT NULL,
            month_summary LONGTEXT NULL,
            supplementary_actions JSON NULL,
            next_month_plan JSON NULL,
            risks JSON NULL,
            provider VARCHAR(50) NULL,
            model VARCHAR(100) NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (analysis_id),
            UNIQUE KEY uk_monthly_project (project_id, month),
            KEY idx_month (month),
            CONSTRAINT fk_monthly_project_analyses_project
                FOREIGN KEY (project_id) REFERENCES projects(project_id)
                ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        with get_cursor() as cursor:
            cursor.execute(sql)

    def ensure_system_settings_table(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS system_settings (
            setting_key VARCHAR(100) NOT NULL,
            setting_value LONGTEXT NULL,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (setting_key)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        with get_cursor() as cursor:
            cursor.execute(sql)

    def init_schema(self, schema_sql: str) -> None:
        statements = [stmt.strip() for stmt in schema_sql.split(";") if stmt.strip()]
        if not statements:
            return

        first_statement, remaining = statements[0], statements[1:]
        admin_conn = get_server_connection()
        try:
            with admin_conn.cursor() as cursor:
                cursor.execute(first_statement)
        finally:
            admin_conn.close()

        with get_cursor() as cursor:
            for statement in remaining:
                cursor.execute(statement)
        self.ensure_monthly_analysis_table()
        self.ensure_llm_model_configs_table()

    def list_projects(self, keyword: str = "") -> List[ProjectRow]:
        sql = """
        SELECT project_id, project_name
        FROM projects
        WHERE (%s = '' OR project_name LIKE CONCAT('%%', %s, '%%'))
        ORDER BY project_name
        """
        with get_cursor() as cursor:
            cursor.execute(sql, (keyword, keyword))
            return [ProjectRow(**row) for row in cursor.fetchall()]

    def get_llm_settings(self) -> LLMSystemSetting:
        self.ensure_llm_model_configs_table()
        sql = """
        SELECT config_id, config_name, provider, model, api_key, base_url, is_active
        FROM llm_model_configs
        WHERE is_active = 1
        ORDER BY updated_at DESC, config_id DESC
        LIMIT 1
        """
        with get_cursor() as cursor:
            cursor.execute(sql)
            row = cursor.fetchone()
        if row:
            return LLMSystemSetting(
                config_id=row["config_id"],
                config_name=row["config_name"],
                provider=row["provider"],
                model=row["model"],
                api_key=row["api_key"] or "",
                base_url=row["base_url"] or "",
                is_active=bool(row["is_active"]),
            )
        legacy = self.get_legacy_llm_settings()
        legacy.config_name = legacy.config_name or legacy.model
        legacy.is_active = True
        self.save_llm_config(legacy)
        return self.get_llm_settings()

    def get_legacy_llm_settings(self) -> LLMSystemSetting:
        self.ensure_system_settings_table()
        sql = """
        SELECT setting_key, setting_value
        FROM system_settings
        WHERE setting_key IN ('llm_provider', 'llm_model', 'llm_api_key', 'llm_base_url')
        """
        values = {
            "provider": "gemini",
            "config_name": "",
            "model": settings.gemini_model,
            "api_key": settings.gemini_api_key,
            "base_url": "",
        }
        with get_cursor() as cursor:
            cursor.execute(sql)
            for row in cursor.fetchall():
                key = row["setting_key"]
                value = row["setting_value"] or ""
                if key == "llm_provider":
                    values["provider"] = value
                elif key == "llm_model":
                    values["model"] = value
                    values["config_name"] = value
                elif key == "llm_api_key":
                    values["api_key"] = value
                elif key == "llm_base_url":
                    values["base_url"] = value
        return LLMSystemSetting(**values)

    def save_llm_settings(self, llm: LLMSystemSetting) -> None:
        self.save_llm_config(llm)

    def list_llm_configs(self) -> List[LLMSystemSetting]:
        self.ensure_llm_model_configs_table()
        sql = """
        SELECT config_id, config_name, provider, model, api_key, base_url, is_active
        FROM llm_model_configs
        ORDER BY is_active DESC, updated_at DESC, config_id DESC
        """
        with get_cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
        if not rows:
            active = self.get_llm_settings()
            return [active]
        return [
            LLMSystemSetting(
                config_id=row["config_id"],
                config_name=row["config_name"],
                provider=row["provider"],
                model=row["model"],
                api_key=row["api_key"] or "",
                base_url=row["base_url"] or "",
                is_active=bool(row["is_active"]),
            )
            for row in rows
        ]

    def save_llm_config(self, llm: LLMSystemSetting) -> None:
        self.ensure_llm_model_configs_table()
        config_name = (llm.config_name or llm.model or llm.provider).strip()
        if not config_name:
            config_name = "default"
        if llm.is_active:
            with get_cursor() as cursor:
                cursor.execute("UPDATE llm_model_configs SET is_active = 0")
        sql = """
        INSERT INTO llm_model_configs (config_id, config_name, provider, model, api_key, base_url, is_active)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            config_name = VALUES(config_name),
            provider = VALUES(provider),
            model = VALUES(model),
            api_key = VALUES(api_key),
            base_url = VALUES(base_url),
            is_active = VALUES(is_active)
        """
        with get_cursor() as cursor:
            cursor.execute(
                sql,
                (
                    llm.config_id,
                    config_name,
                    llm.provider,
                    llm.model,
                    llm.api_key,
                    llm.base_url,
                    1 if llm.is_active else 0,
                ),
            )

    def save_legacy_llm_settings(self, llm: LLMSystemSetting) -> None:
        self.ensure_system_settings_table()
        sql = """
        INSERT INTO system_settings (setting_key, setting_value)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)
        """
        pairs = [
            ("llm_provider", llm.provider),
            ("llm_model", llm.model),
            ("llm_api_key", llm.api_key),
            ("llm_base_url", llm.base_url),
        ]
        with get_cursor() as cursor:
            for key, value in pairs:
                cursor.execute(sql, (key, value))

    def load_project_catalog(self) -> List[Dict[str, Any]]:
        sql = """
        SELECT project_id, project_name, normalized_name, project_name AS match_name, 'project' AS match_type
        FROM projects
        UNION ALL
        SELECT p.project_id, p.project_name, a.normalized_alias AS normalized_name, a.alias_name AS match_name, 'alias' AS match_type
        FROM project_aliases a
        JOIN projects p ON a.project_id = p.project_id
        """
        with get_cursor() as cursor:
            cursor.execute(sql)
            rows = list(cursor.fetchall())
            return rows

    def load_project_name_map(self) -> Dict[str, Dict[str, Any]]:
        sql = "SELECT project_id, project_name FROM projects"
        with get_cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
        return {row["project_name"].strip(): row for row in rows if row["project_name"]}

    def find_best_project(self, project_name: str) -> Optional[Dict[str, Any]]:
        catalog = self.load_project_catalog()
        return self.find_best_project_in_catalog(project_name, catalog)

    def find_best_project_in_catalog(self, project_name: str, catalog: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        best_item: Optional[Dict[str, Any]] = None
        best_score = 0.0
        for item in catalog:
            score = score_project_name(project_name, item["match_name"])
            if score > best_score:
                best_score = score
                best_item = item
        if best_item:
            best_item = {**best_item, "score": best_score}
        return best_item

    def match_project(self, project_name: str) -> Dict[str, Any]:
        matched = self.find_best_project(project_name)
        return self.build_match_result(matched)

    def match_project_in_catalog(self, project_name: str, catalog: List[Dict[str, Any]]) -> Dict[str, Any]:
        matched = self.find_best_project_in_catalog(project_name, catalog)
        return self.build_match_result(matched)

    def build_match_result(self, matched: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not matched:
            return {"match_status": "new", "match_confidence": 0}
        score = float(matched["score"])
        status = "auto" if score >= 0.90 else "confirm" if score >= 0.70 else "new"
        return {
            "project_id": matched["project_id"],
            "project_name": matched["project_name"],
            "match_confidence": score,
            "match_status": status,
        }

    def ensure_project(self, project_name: str) -> Dict[str, Any]:
        sql = """
        INSERT INTO projects (project_name, normalized_name, alias_names)
        VALUES (%s, %s, JSON_ARRAY())
        ON DUPLICATE KEY UPDATE project_name = VALUES(project_name)
        """
        with get_cursor() as cursor:
            cursor.execute(sql, (project_name, normalize_name(project_name)))
            project_id = cursor.lastrowid
            if not project_id:
                cursor.execute("SELECT project_id FROM projects WHERE project_name = %s", (project_name,))
                project_id = cursor.fetchone()["project_id"]
        return {"project_id": project_id, "project_name": project_name, "score": 1.0}

    def save_project_alias(self, project_id: int, alias_name: str, source: str = "confirmed", confidence: float = 1.0) -> None:
        alias_name = alias_name.strip()
        if not alias_name:
            return
        sql = """
        INSERT INTO project_aliases (project_id, alias_name, normalized_alias, source, confidence)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            project_id = VALUES(project_id),
            normalized_alias = VALUES(normalized_alias),
            source = VALUES(source),
            confidence = VALUES(confidence)
        """
        with get_cursor() as cursor:
            cursor.execute(sql, (project_id, alias_name, normalize_name(alias_name), source, confidence))

    def save_weekly_report(self, project_id: int, week_start: str, item: ReportBlock, summary_text: str = "") -> None:
        sql = """
        INSERT INTO weekly_reports (
            project_id, week_start, raw_text, current_progress, next_plan, summary_text, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, NOW())
        ON DUPLICATE KEY UPDATE
            raw_text = VALUES(raw_text),
            current_progress = VALUES(current_progress),
            next_plan = VALUES(next_plan),
            summary_text = VALUES(summary_text),
            updated_at = NOW()
        """
        with get_cursor() as cursor:
            cursor.execute(
                sql,
                (project_id, week_start, item.raw_text, item.current_progress, item.next_plan, summary_text),
            )

    def delete_week(self, week_start: str) -> int:
        sql = "DELETE FROM weekly_reports WHERE week_start = %s"
        with get_cursor() as cursor:
            affected = cursor.execute(sql, (week_start,))
        return affected

    def delete_cell(self, project_id: int, week_start: str) -> int:
        sql = "DELETE FROM weekly_reports WHERE project_id = %s AND week_start = %s"
        with get_cursor() as cursor:
            affected = cursor.execute(sql, (project_id, week_start))
        return affected

    def delete_project(self, project_id: int) -> int:
        sql = "DELETE FROM projects WHERE project_id = %s"
        with get_cursor() as cursor:
            affected = cursor.execute(sql, (project_id,))
        return affected

    def update_project_name(self, project_id: int, project_name: str) -> int:
        sql = "UPDATE projects SET project_name = %s, normalized_name = %s WHERE project_id = %s"
        with get_cursor() as cursor:
            affected = cursor.execute(sql, (project_name, normalize_name(project_name), project_id))
        return affected

    def update_cell(self, project_id: int, week_start: str, current_progress: str, next_plan: str) -> int:
        sql = """
        INSERT INTO weekly_reports (
            project_id, week_start, raw_text, current_progress, next_plan, summary_text, updated_at
        ) VALUES (%s, %s, %s, %s, %s, '', NOW())
        ON DUPLICATE KEY UPDATE
            raw_text = VALUES(raw_text),
            current_progress = VALUES(current_progress),
            next_plan = VALUES(next_plan),
            updated_at = NOW()
        """
        raw_text = "\n".join([current_progress.strip(), next_plan.strip()]).strip()
        with get_cursor() as cursor:
            affected = cursor.execute(sql, (project_id, week_start, raw_text, current_progress, next_plan))
        return affected

    def list_matrix(self, keyword: str = "", week_start: str = "", week_end: str = "") -> List[ProjectMatrixRow]:
        project_sql = """
        SELECT project_id, project_name
        FROM projects
        WHERE (%s = '' OR project_name LIKE CONCAT('%%', %s, '%%'))
        ORDER BY project_name
        """
        with get_cursor() as cursor:
            cursor.execute(project_sql, (keyword, keyword))
            projects = cursor.fetchall()

            rows: Dict[int, ProjectMatrixRow] = {
                item["project_id"]: ProjectMatrixRow(
                    project_id=item["project_id"],
                    project_name=item["project_name"],
                    weeks=[],
                )
                for item in projects
            }
            if not rows:
                return []

            report_sql = """
            SELECT
                r.project_id,
                r.week_start,
                COALESCE(r.current_progress, '') AS current_progress,
                COALESCE(r.next_plan, '') AS next_plan,
                COALESCE(r.summary_text, '') AS summary_text
            FROM weekly_reports r
            WHERE r.project_id IN %s
              AND (%s = '' OR r.week_start >= %s)
              AND (%s = '' OR r.week_start <= %s)
            ORDER BY r.project_id, r.week_start
            """
            cursor.execute(report_sql, (tuple(rows.keys()), week_start, week_start, week_end, week_end))
            for item in cursor.fetchall():
                row = rows.get(item["project_id"])
                if not row:
                    continue
                row.weeks.append(
                    WeekCell(
                        week_start=str(item["week_start"]),
                        current_progress=item["current_progress"],
                        next_plan=item["next_plan"],
                        summary_text=item["summary_text"],
                    )
                )
        return list(rows.values())

    def _month_bounds(self, month: str) -> tuple[str, str]:
        year_text, month_text = month.split("-")
        start = date(int(year_text), int(month_text), 1)
        if start.month == 12:
            end = date(start.year + 1, 1, 1)
        else:
            end = date(start.year, start.month + 1, 1)
        return start.isoformat(), end.isoformat()

    def load_monthly_analyses(self, month: str, project_ids: List[int]) -> Dict[int, MonthlyAnalysisResult]:
        if not project_ids:
            return {}
        self.ensure_monthly_analysis_table()
        sql = """
        SELECT
            a.project_id,
            p.project_name,
            a.month_summary,
            a.supplementary_actions,
            a.next_month_plan,
            a.risks
        FROM monthly_project_analyses a
        JOIN projects p ON a.project_id = p.project_id
        WHERE a.month = %s AND a.project_id IN %s
        """
        result: Dict[int, MonthlyAnalysisResult] = {}
        with get_cursor() as cursor:
            cursor.execute(sql, (month, tuple(project_ids)))
            for row in cursor.fetchall():
                result[row["project_id"]] = MonthlyAnalysisResult(
                    project_id=row["project_id"],
                    project_name=row["project_name"],
                    month=month,
                    month_summary=row["month_summary"] or "",
                    supplementary_actions=json.loads(row["supplementary_actions"] or "[]"),
                    next_month_plan=json.loads(row["next_month_plan"] or "[]"),
                    risks=json.loads(row["risks"] or "[]"),
                )
        return result

    def list_monthly_review(self, month: str, keyword: str = "") -> List[MonthlyProjectRow]:
        month_start, next_month_start = self._month_bounds(month)
        sql = """
        SELECT
            p.project_id,
            p.project_name,
            r.week_start,
            COALESCE(r.current_progress, '') AS current_progress,
            COALESCE(r.next_plan, '') AS next_plan
        FROM weekly_reports r
        JOIN projects p ON p.project_id = r.project_id
        WHERE r.week_start >= %s
          AND r.week_start < %s
          AND (%s = '' OR p.project_name LIKE CONCAT('%%', %s, '%%'))
        ORDER BY p.project_name, r.week_start
        """
        rows: Dict[int, MonthlyProjectRow] = {}
        with get_cursor() as cursor:
            cursor.execute(sql, (month_start, next_month_start, keyword, keyword))
            for item in cursor.fetchall():
                project_id = item["project_id"]
                row = rows.setdefault(
                    project_id,
                    MonthlyProjectRow(
                        project_id=project_id,
                        project_name=item["project_name"],
                        month=month,
                        progress_digest="",
                        plan_digest="",
                        weeks=[],
                    ),
                )
                if item["week_start"]:
                    week = MonthlyWeekItem(
                        week_start=str(item["week_start"]),
                        current_progress=item["current_progress"],
                        next_plan=item["next_plan"],
                    )
                    row.weeks.append(week)

            if rows:
                analysis_sql = """
                SELECT
                    a.project_id,
                    p.project_name,
                    a.month_summary,
                    a.supplementary_actions,
                    a.next_month_plan,
                    a.risks
                FROM monthly_project_analyses a
                JOIN projects p ON a.project_id = p.project_id
                WHERE a.month = %s AND a.project_id IN %s
                """
                cursor.execute(analysis_sql, (month, tuple(rows.keys())))
                analyses = {
                    item["project_id"]: MonthlyAnalysisResult(
                        project_id=item["project_id"],
                        project_name=item["project_name"],
                        month=month,
                        month_summary=item["month_summary"] or "",
                        supplementary_actions=json.loads(item["supplementary_actions"] or "[]"),
                        next_month_plan=json.loads(item["next_month_plan"] or "[]"),
                        risks=json.loads(item["risks"] or "[]"),
                    )
                    for item in cursor.fetchall()
                }
            else:
                analyses = {}

            for row in rows.values():
                progress_items = []
                plan_items = []
                for week in row.weeks:
                    if (week.current_progress or "").strip():
                        progress_items.append(f"[{week.week_start}] {week.current_progress.strip()}")
                    if (week.next_plan or "").strip():
                        plan_items.append(f"[{week.week_start}] {week.next_plan.strip()}")
                row.progress_digest = "\n".join(progress_items)
                row.plan_digest = "\n".join(plan_items)
                row.analysis = analyses.get(row.project_id)
        return list(rows.values())

    def get_monthly_project_row(self, project_id: int, month: str) -> Optional[MonthlyProjectRow]:
        rows = self.list_monthly_review(month=month, keyword="")
        for row in rows:
            if row.project_id == project_id:
                return row
        return None

    def get_monthly_analysis(self, project_id: int, month: str, project_name: str = "") -> Optional[MonthlyAnalysisResult]:
        self.ensure_monthly_analysis_table()
        sql = """
        SELECT
            p.project_name,
            a.month_summary,
            a.supplementary_actions,
            a.next_month_plan,
            a.risks
        FROM monthly_project_analyses a
        JOIN projects p ON a.project_id = p.project_id
        WHERE a.project_id = %s AND a.month = %s
        """
        with get_cursor() as cursor:
            cursor.execute(sql, (project_id, month))
            row = cursor.fetchone()
        if not row:
            return None
        return MonthlyAnalysisResult(
            project_id=project_id,
            project_name=row["project_name"] or project_name,
            month=month,
            month_summary=row["month_summary"] or "",
            supplementary_actions=json.loads(row["supplementary_actions"] or "[]"),
            next_month_plan=json.loads(row["next_month_plan"] or "[]"),
            risks=json.loads(row["risks"] or "[]"),
        )

    def save_monthly_analysis(self, analysis: MonthlyAnalysisResult, llm: LLMSystemSetting) -> None:
        self.ensure_monthly_analysis_table()
        sql = """
        INSERT INTO monthly_project_analyses (
            project_id, month, month_summary, supplementary_actions, next_month_plan, risks, provider, model
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            month_summary = VALUES(month_summary),
            supplementary_actions = VALUES(supplementary_actions),
            next_month_plan = VALUES(next_month_plan),
            risks = VALUES(risks),
            provider = VALUES(provider),
            model = VALUES(model),
            updated_at = NOW()
        """
        with get_cursor() as cursor:
            cursor.execute(
                sql,
                (
                    analysis.project_id,
                    analysis.month,
                    analysis.month_summary,
                    json.dumps(analysis.supplementary_actions, ensure_ascii=False),
                    json.dumps(analysis.next_month_plan, ensure_ascii=False),
                    json.dumps(analysis.risks, ensure_ascii=False),
                    llm.provider,
                    llm.model,
                ),
            )
