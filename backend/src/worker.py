"""分析任务 worker。

中断恢复要点：
- 领取（claim_next_job）是数据库条件 UPDATE，并发 worker / 重复投递只有一个成功；
- 后台心跳线程为持有的任务续租，租约未到期的任务不会被别人抢走；
- 进程崩溃后心跳停止，租约到期，reaper 把孤儿任务重新入队，由任意 worker 接手；
- 完成走幂等条件 UPDATE + 留痕查重，结果文件原子写入；写文件失败时任务保持
  running 并重新入队，下一次接手直接复用已算出的结果，不重复分析。
"""
import logging
import threading
import time
import traceback
from pathlib import Path

from .config import settings
from .config.database import Base, SessionLocal, engine
from .models import AnalysisRun, Experiment, Observation
from .services import run_recovery as recovery
from .services.audit_service import log
from .services.run_service import queue
from .services.statistics_service import analyze

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("worker")


def _heartbeat_loop(stop_event: threading.Event, run_id: int, worker_id: str):
    while not stop_event.wait(settings.HEARTBEAT_INTERVAL_SECONDS):
        try:
            with SessionLocal() as hb_db:
                if not recovery.heartbeat(hb_db, run_id, worker_id):
                    logger.warning("任务 %s 租约已丢失，停止心跳", run_id)
                    return
        except Exception:
            logger.exception("任务 %s 心跳异常", run_id)


def _process(run: AnalysisRun, worker_id: str) -> None:
    run_id = run.id
    stop_event = threading.Event()
    hb_thread = threading.Thread(
        target=_heartbeat_loop, args=(stop_event, run_id, worker_id), daemon=True
    )
    hb_thread.start()
    try:
        with SessionLocal() as db:
            current = db.get(AnalysisRun, run_id)

            # 幂等：接手到已经算出结果（上次只在写文件时失败）的任务，直接复用结果。
            # 结果已在库中时即便领取次数超限也应收尾完成，避免卡在只差写文件的状态。
            result = current.result if current.result else None
            if result is None:
                if recovery.give_up_if_exhausted(db, run):
                    logger.error("任务 %s 重试耗尽，标记失败", run_id)
                    return
                current = db.get(AnalysisRun, run_id)
                exp = db.get(Experiment, current.experiment_id)
                observations = (
                    db.query(Observation).filter_by(dataset_id=exp.dataset_id).all()
                )
                result = analyze(observations, exp.alpha, exp.cuped)
                current.result = result
                db.commit()

            # 写结果前最后确认租约仍在自己手里，防止与接手者并发写
            if not recovery.still_owned(db, run_id, worker_id):
                logger.warning("任务 %s 完成前租约已失效，放弃本次提交", run_id)
                return

            try:
                recovery.write_artifact(run_id, result)
            except OSError as error:
                # 文件写入失败：状态保持 running，重新入队等待重试，不记完成留痕。
                # 入队本身失败也不改变状态，租约到期后 reaper 仍会再次回收该任务。
                logger.error("任务 %s 结果文件写入失败，将重新入队：%s", run_id, error)
                try:
                    queue.rpush(settings.JOB_QUEUE_KEY, run_id)
                except Exception:
                    logger.exception("任务 %s 重新入队失败，等待租约回收", run_id)
                return

            if not recovery.complete_run(db, run_id, worker_id, result):
                logger.warning("任务 %s 已被其他流程完成，本次结果丢弃", run_id)
                return

            # 留痕幂等：同一任务的 analysis.completed 只写一条
            if not recovery.completion_audit_exists(db, run_id):
                log(db, "worker", "analysis.completed", run_id)
            db.commit()
            logger.info("任务 %s 分析完成", run_id)
    except Exception as error:
        traceback.print_exc()
        with SessionLocal() as db:
            recovery.fail_run(db, run_id, worker_id, str(error))
    finally:
        stop_event.set()
        hb_thread.join(timeout=2)
        try:
            recovery.clear_requeue_lock(queue, run_id)
        except Exception:
            logger.exception("任务 %s 清理恢复标记失败", run_id)


def main() -> None:
    Base.metadata.create_all(engine)
    from .config.migrations import ensure_run_recovery_schema, recover_orphan_runs

    ensure_run_recovery_schema()
    try:
        recover_orphan_runs()
    except Exception:
        # 启动恢复失败不阻断消费；主循环的租约回收会持续兜底
        logger.exception("启动任务恢复失败，依赖主循环租约回收")
    Path(settings.ARTIFACT_DIR).mkdir(parents=True, exist_ok=True)
    worker_id = recovery.worker_identity()
    logger.info("worker %s 启动", worker_id)
    while True:
        try:
            Path(settings.ARTIFACT_DIR, "heartbeat").write_text(str(time.time()))
        except OSError:
            # 心跳文件写失败不应拖垮消费循环；处理任务时的产物写入另有失败重试
            logger.exception("心跳文件写入失败")
        try:
            # 先回收租约过期的中断任务，再取队列消息
            with SessionLocal() as db:
                recovered = recovery.requeue_stale_runs(db, queue)
                if recovered:
                    logger.info("重新入队中断任务：%s", recovered)
            job = queue.blpop(settings.JOB_QUEUE_KEY, timeout=int(settings.REAPER_INTERVAL_SECONDS))
        except Exception:
            logger.exception("worker 轮询异常，稍后重试")
            time.sleep(settings.REAPER_INTERVAL_SECONDS)
            continue
        if not job:
            continue
        try:
            run_id = int(job[1])
        except ValueError:
            logger.error("忽略非法队列消息：%r", job[1])
            continue
        with SessionLocal() as db:
            run = recovery.claim_next_job(db, worker_id)
        if run is None:
            # 重复投递或任务已被其他 worker 领取/已完成：消息直接丢弃，不重复处理
            logger.info("队列消息 %s 无可领取任务，忽略", run_id)
            continue
        # 队列里可能有同一任务的重复消息，也可能有其他任务的残留消息；
        # 领取只认数据库状态，若领取到的是另一条任务，把本消息放回队首稍后处理
        if run.id != run_id:
            queue.lpush(settings.JOB_QUEUE_KEY, run_id)
        logger.info("worker %s 领取任务 %s（第 %s 次）", worker_id, run.id, run.attempts)
        _process(run, worker_id)


if __name__ == "__main__":
    main()
