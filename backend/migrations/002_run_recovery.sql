-- 002: 任务中断恢复所需的租约与重试字段。
-- 新库由 SQLAlchemy metadata 直接建出这些列；本脚本用于已存在的库，可重复执行。
ALTER TABLE analysis_runs ADD COLUMN IF NOT EXISTS locked_by VARCHAR NOT NULL DEFAULT '';
ALTER TABLE analysis_runs ADD COLUMN IF NOT EXISTS locked_at VARCHAR NOT NULL DEFAULT '';
ALTER TABLE analysis_runs ADD COLUMN IF NOT EXISTS attempts INTEGER NOT NULL DEFAULT 0;

-- 便于恢复扫描按状态与租约时间定位孤儿任务
CREATE INDEX IF NOT EXISTS analysis_runs_status_lease_idx
    ON analysis_runs (status, locked_at);
