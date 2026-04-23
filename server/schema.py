SCHEMA_SQL = """
CREATE DATABASE IF NOT EXISTS pmo DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS projects (
    project_id BIGINT NOT NULL AUTO_INCREMENT,
    project_name VARCHAR(200) NOT NULL,
    normalized_name VARCHAR(200) NOT NULL,
    alias_names JSON NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (project_id),
    UNIQUE KEY uk_project_name (project_name),
    KEY idx_normalized_name (normalized_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS weekly_reports (
    report_id BIGINT NOT NULL AUTO_INCREMENT,
    project_id BIGINT NOT NULL,
    week_start DATE NOT NULL,
    raw_text LONGTEXT NOT NULL,
    current_progress LONGTEXT NULL,
    next_plan LONGTEXT NULL,
    summary_text LONGTEXT NULL,
    source_type VARCHAR(32) NOT NULL DEFAULT 'import',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (report_id),
    UNIQUE KEY uk_project_week (project_id, week_start),
    KEY idx_week_start (week_start),
    CONSTRAINT fk_weekly_reports_project
        FOREIGN KEY (project_id) REFERENCES projects(project_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""
