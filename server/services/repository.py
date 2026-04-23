import json
from typing import Any, Dict, List, Optional

from server.config import settings
from server.database import get_cursor, get_server_connection
from server.models import ProjectMatrixRow, ProjectRow, ReportBlock, WeekCell
from server.services.matcher import normalize_name, score_project_name


class ProjectRepository:
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

    def load_project_catalog(self) -> List[Dict[str, Any]]:
        sql = "SELECT project_id, project_name, normalized_name, alias_names FROM projects"
        with get_cursor() as cursor:
            cursor.execute(sql)
            rows = list(cursor.fetchall())
            for item in rows:
                alias_names = item.get("alias_names") or "[]"
                try:
                    item["alias_names"] = json.loads(alias_names)
                except json.JSONDecodeError:
                    item["alias_names"] = []
            return rows

    def load_project_name_map(self) -> Dict[str, Dict[str, Any]]:
        sql = "SELECT project_id, project_name FROM projects"
        with get_cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
        return {row["project_name"].strip(): row for row in rows if row["project_name"]}

    def find_best_project(self, project_name: str) -> Optional[Dict[str, Any]]:
        catalog = self.load_project_catalog()
        best_item: Optional[Dict[str, Any]] = None
        best_score = 0.0
        for item in catalog:
            score = score_project_name(project_name, item["project_name"], item.get("alias_names"))
            if score > best_score:
                best_score = score
                best_item = item
        if best_item:
            best_item = {**best_item, "score": best_score}
        return best_item

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

    def update_project_name(self, project_id: int, project_name: str) -> int:
        sql = "UPDATE projects SET project_name = %s, normalized_name = %s WHERE project_id = %s"
        with get_cursor() as cursor:
            affected = cursor.execute(sql, (project_name, normalize_name(project_name), project_id))
        return affected

    def update_cell(self, project_id: int, week_start: str, current_progress: str, next_plan: str) -> int:
        sql = """
        UPDATE weekly_reports
        SET current_progress = %s, next_plan = %s, updated_at = NOW()
        WHERE project_id = %s AND week_start = %s
        """
        with get_cursor() as cursor:
            affected = cursor.execute(sql, (current_progress, next_plan, project_id, week_start))
        return affected

    def list_matrix(self, keyword: str = "", week_start: str = "", week_end: str = "") -> List[ProjectMatrixRow]:
        sql = """
        SELECT
            p.project_id,
            p.project_name,
            r.week_start,
            COALESCE(r.current_progress, '') AS current_progress,
            COALESCE(r.next_plan, '') AS next_plan,
            COALESCE(r.summary_text, '') AS summary_text
        FROM projects p
        LEFT JOIN weekly_reports r ON p.project_id = r.project_id
        WHERE (%s = '' OR p.project_name LIKE CONCAT('%%', %s, '%%'))
          AND (%s = '' OR r.week_start >= %s OR r.week_start IS NULL)
          AND (%s = '' OR r.week_start <= %s OR r.week_start IS NULL)
        ORDER BY p.project_name, r.week_start
        """
        rows: Dict[int, ProjectMatrixRow] = {}
        with get_cursor() as cursor:
            cursor.execute(sql, (keyword, keyword, week_start, week_start, week_end, week_end))
            for item in cursor.fetchall():
                project_id = item["project_id"]
                row = rows.setdefault(
                    project_id,
                    ProjectMatrixRow(project_id=project_id, project_name=item["project_name"], weeks=[]),
                )
                if item["week_start"]:
                    row.weeks.append(
                        WeekCell(
                            week_start=str(item["week_start"]),
                            current_progress=item["current_progress"],
                            next_plan=item["next_plan"],
                            summary_text=item["summary_text"],
                        )
                    )
        return list(rows.values())
