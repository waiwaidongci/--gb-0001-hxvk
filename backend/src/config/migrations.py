"""轻量幂等结构升级：只补列与索引，不改已有数据。"""
import logging
from sqlalchemy import inspect, text
from ..config.database import engine
from . import settings

logger = logging.getLogger(__name__)


def ensure_run_recovery_schema() -> None:
    """为已存在的 analysis_runs 表补齐中断恢复字段（新库 metadata 已包含）。"""
    inspector = inspect(engine)
    if "analysis_runs" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("analysis_runs")}
    statements = []
    if "locked_by" not in existing:
        statements.append("ALTER TABLE analysis_runs ADD COLUMN locked_by VARCHAR NOT NULL DEFAULT ''")
    if "locked_at" not in existing:
        statements.append("ALTER TABLE analysis_runs ADD COLUMN locked_at VARCHAR NOT NULL DEFAULT ''")
    if "attempts" not in existing:
        statements.append("ALTER TABLE analysis_runs ADD COLUMN attempts INTEGER NOT NULL DEFAULT 0")
    statements.append(
        "CREATE INDEX IF NOT EXISTS analysis_runs_status_lease_idx "
        "ON analysis_runs (status, locked_at)"
    )
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
    if statements:
        logger.info("analysis_runs 恢复字段已就绪：%s", len(statements))


def recover_orphan_runs() -> list[int]:
    """启动时把旧版本遗留、卡死在 running 的任务置回 queued 等待重新投递。"""
    from ..services.run_service import queue
    from ..constants.status import RunStatus

    with engine.begin() as conn:
        ids = [
            r[0]
            for r in conn.execute(
                text(
                    "SELECT id FROM analysis_runs WHERE status = :running AND "
                    "(locked_at = '' OR NULLIF(locked_at, '')::timestamptz "
                    "< now() - make_interval(secs => :secs))"
                ),
                {"running": RunStatus.RUNNING, "secs": settings.LEASE_TIMEOUT_SECONDS},
            ).all()
        ]
        if ids:
            conn.execute(
                text(
                    "UPDATE analysis_runs SET status = :queued, locked_by = '', locked_at = '' "
                    "WHERE id = ANY(:ids)"
                ),
                {"queued": RunStatus.QUEUED, "ids": ids},
            )
    for rid in ids:
        queue.rpush(settings.JOB_QUEUE_KEY, rid)
        logger.warning("启动恢复：遗留 running 任务 %s 已重新排队", rid)
    return ids
