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

CREATE TABLE IF NOT EXISTS project_aliases (
    alias_id BIGINT NOT NULL AUTO_INCREMENT,
    project_id BIGINT NOT NULL,
    alias_name VARCHAR(200) NOT NULL,
    normalized_alias VARCHAR(200) NOT NULL,
    source VARCHAR(32) NOT NULL DEFAULT 'confirmed',
    confidence DECIMAL(5,4) NOT NULL DEFAULT 1.0000,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (alias_id),
    UNIQUE KEY uk_alias_name (alias_name),
    KEY idx_normalized_alias (normalized_alias),
    KEY idx_project_id (project_id),
    CONSTRAINT fk_project_aliases_project
        FOREIGN KEY (project_id) REFERENCES projects(project_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS system_settings (
    setting_key VARCHAR(100) NOT NULL,
    setting_value LONGTEXT NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (setting_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""
