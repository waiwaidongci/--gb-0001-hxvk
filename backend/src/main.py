import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text
from .config.database import Base,engine
from .config.settings import SEED_DEMO
from . import models
from .routes import auth,datasets,experiments,runs,decisions,audits
from .middlewares.errors import ErrorMiddleware
from .middlewares.rate_limit import RateLimitMiddleware
from .services.run_service import queue
@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    from .config.migrations import ensure_run_recovery_schema, recover_orphan_runs
    ensure_run_recovery_schema()
    try:
        recover_orphan_runs()
    except Exception:
        # 启动恢复失败不应阻断 API；worker 的租约回收会兜底处理孤儿任务
        logging.exception("启动任务恢复失败，等待 worker 租约回收")
    if SEED_DEMO:
        try:
            from scripts.seed_demo import seed
            seed()
        except Exception: logging.exception("demo seed failed")
    yield
app=FastAPI(title="岚桥实验放量台",lifespan=lifespan)
app.add_middleware(ErrorMiddleware)
app.add_middleware(RateLimitMiddleware)
for route in [auth,datasets,experiments,runs,decisions,audits]: app.include_router(route.router)
@app.get("/health")
def health():
    with engine.connect() as conn: conn.execute(text("select 1"))
    queue.ping()
    return {"status":"healthy","service":"lift-lab"}
