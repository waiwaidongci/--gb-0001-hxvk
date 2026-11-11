import os
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg://lift:lift@db/lift")
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
JWT_SECRET = os.environ.get("JWT_SECRET", "local-development-change-this-key")
SEED_DEMO = os.environ.get("SEED_DEMO", "true").lower() == "true"
# 任务租约：心跳间隔与租约超时。租约需长于单次分析的最长耗时，
# 进程中断后心跳停止、租约到期，任务可被其他 worker 重新接手
ARTIFACT_DIR = os.environ.get("ARTIFACT_DIR", "/artifacts")
JOB_QUEUE_KEY = os.environ.get("JOB_QUEUE_KEY", "lift:jobs")
LEASE_TIMEOUT_SECONDS = float(os.environ.get("LEASE_TIMEOUT_SECONDS", "120"))
HEARTBEAT_INTERVAL_SECONDS = float(os.environ.get("HEARTBEAT_INTERVAL_SECONDS", "30"))
MAX_ATTEMPTS = int(os.environ.get("MAX_ATTEMPTS", "3"))
REAPER_INTERVAL_SECONDS = float(os.environ.get("REAPER_INTERVAL_SECONDS", "5"))
