"""任务领取、租约续租与中断恢复。

所有状态流转都以单条条件 UPDATE 完成，保证并发 worker、重复投递与
worker 进程中断场景下：
- 排队任务只有一个 worker 能领取成功；
- 仍在正常处理（租约未到期）的任务不会被其他 worker 抢走；
- 中断后租约到期的 running 任务可被重新接手，且每个过期周期只重新入队一次；
- 已完成的任务永不重复分析、不重复写完成留痕。
"""
import json
import logging
import uuid
from pathlib import Path

from sqlalchemy import text

from ..config import settings
from ..constants.status import RunStatus
from ..models import AnalysisRun

logger = logging.getLogger(__name__)


def worker_identity() -> str:
    return f"{uuid.getnode():x}-{uuid.uuid4().hex[:8]}"


def requeue_lock_key(run_id: int) -> str:
    return f"lift:requeue:{run_id}"


def _stale_clause() -> str:
    """租约过期判定：locked_at 为时间文本，空串视为未加锁。"""
    return (
        "(locked_at = '' OR "
        "NULLIF(locked_at, '')::timestamptz < now() - make_interval(secs => :secs))"
    )


def claim_next_job(db, worker_id: str):
    """原子领取下一条可处理任务，返回 AnalysisRun 或 None。

    可领取的任务：
    1. status=queued（含重复投递，只会被领取一次）；
    2. status=running 但租约已过期（worker 中断后留下的孤儿任务）。
    正在正常处理、已完成、已失败的任务不会被领取。
    """
    sql = text(
        f"""
        UPDATE analysis_runs
           SET status = :running,
               locked_by = :worker,
               locked_at = now()::text,
               attempts = attempts + 1
         WHERE id = (
                SELECT id FROM analysis_runs
                 WHERE status = :queued
                    OR (status = :running AND {_stale_clause()})
                 ORDER BY id
                 FOR UPDATE SKIP LOCKED
                 LIMIT 1
               )
        RETURNING id
        """
    )
    row = db.execute(
        sql,
        {
            "running": RunStatus.RUNNING,
            "worker": worker_id,
            "queued": RunStatus.QUEUED,
            "secs": settings.LEASE_TIMEOUT_SECONDS,
        },
    ).first()
    db.commit()
    if not row:
        return None
    return db.get(AnalysisRun, row[0])


def clear_requeue_lock(queue, run_id: int) -> None:
    """任务被成功领取后清掉恢复标记，允许下次中断时再次恢复。"""
    queue.delete(requeue_lock_key(run_id))


def heartbeat(db, run_id: int, worker_id: str) -> bool:
    """续租。只有锁的持有者能续上，返回是否仍持有租约。"""
    result = db.execute(
        text(
            "UPDATE analysis_runs SET locked_at = now()::text "
            "WHERE id = :id AND locked_by = :worker AND status = :running"
        ),
        {"id": run_id, "worker": worker_id, "running": RunStatus.RUNNING},
    )
    db.commit()
    return result.rowcount == 1


def still_owned(db, run_id: int, worker_id: str) -> bool:
    """确认当前 worker 仍持有任务租约，用于写结果前的最终校验。"""
    row = db.execute(
        text(
            "SELECT 1 FROM analysis_runs "
            "WHERE id = :id AND locked_by = :worker AND status = :running"
        ),
        {"id": run_id, "worker": worker_id, "running": RunStatus.RUNNING},
    ).first()
    return row is not None


def complete_run(db, run_id: int, worker_id: str, result: dict) -> bool:
    """幂等完成：仅持有者可完成；已完成的任务保持原样，返回是否完成。"""
    run = db.get(AnalysisRun, run_id)
    if not run or run.status == RunStatus.COMPLETED:
        db.rollback()
        return False
    out = db.execute(
        text(
            "UPDATE analysis_runs SET status = :completed, result = CAST(:result AS json) "
            "WHERE id = :id AND locked_by = :worker AND status = :running"
        ),
        {
            "completed": RunStatus.COMPLETED,
            "result": json.dumps(result, ensure_ascii=False),
            "id": run_id,
            "worker": worker_id,
            "running": RunStatus.RUNNING,
        },
    )
    db.commit()
    return out.rowcount == 1


def fail_run(db, run_id: int, worker_id: str, error: str) -> bool:
    """标记失败（分析本身报错或重试耗尽），仅持有者可写。"""
    out = db.execute(
        text(
            "UPDATE analysis_runs SET status = :failed, error = :error "
            "WHERE id = :id AND locked_by = :worker AND status = :running"
        ),
        {
            "failed": RunStatus.FAILED,
            "error": error[:1000],
            "id": run_id,
            "worker": worker_id,
            "running": RunStatus.RUNNING,
        },
    )
    db.commit()
    return out.rowcount == 1


def requeue_stale_runs(db, queue) -> list[int]:
    """扫描租约过期的 running 任务并重新投递队列。

    用 Redis SET NX 锁保证每条孤儿任务在一个过期周期内只重新入队一次；
    任务被重新领取后清锁。队列里即便存在重复消息，领取阶段的条件
    UPDATE 也会天然去重，不会产生重复分析。
    """
    ids = [
        r[0]
        for r in db.execute(
            text(
                "SELECT id FROM analysis_runs "
                f"WHERE status = :running AND {_stale_clause()} ORDER BY id"
            ),
            {"running": RunStatus.RUNNING, "secs": settings.LEASE_TIMEOUT_SECONDS},
        ).all()
    ]
    ttl = int(settings.LEASE_TIMEOUT_SECONDS * 2)
    requeued = []
    for rid in ids:
        if not queue.set(requeue_lock_key(rid), "1", nx=True, ex=ttl):
            continue
        queue.rpush(settings.JOB_QUEUE_KEY, rid)
        requeued.append(rid)
        logger.warning("租约过期，任务 %s 已重新入队等待接手", rid)
    return requeued


def give_up_if_exhausted(db, run: AnalysisRun) -> bool:
    """领取次数超过上限时终止自动重试，避免坏任务无限循环。

    第 MAX_ATTEMPTS 次领取仍允许处理；再次中断后产生的下一次领取才放弃。
    """
    if run.attempts <= settings.MAX_ATTEMPTS:
        return False
    db.execute(
        text(
            "UPDATE analysis_runs SET status = :failed, "
            "error = '重试次数已达上限，最后一次中断后未完成，请人工检查后重新运行' "
            "WHERE id = :id AND status = :running"
        ),
        {"failed": RunStatus.FAILED, "id": run.id, "running": RunStatus.RUNNING},
    )
    db.commit()
    return True


def write_artifact(run_id: int, result: dict) -> Path:
    """原子写入结果文件：先写临时文件再 rename，失败可安全重试。"""
    directory = Path(settings.ARTIFACT_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"run-{run_id}.json"
    tmp = directory / f".run-{run_id}.json.tmp-{uuid.uuid4().hex}"
    tmp.write_text(json.dumps(result, ensure_ascii=False))
    tmp.replace(target)
    return target


def completion_audit_exists(db, run_id: int) -> bool:
    from ..models import Audit

    return (
        db.query(Audit)
        .filter_by(action="analysis.completed", target=str(run_id))
        .first()
        is not None
    )
