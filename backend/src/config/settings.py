import os
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg://lift:lift@db/lift")
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
JWT_SECRET = os.environ.get("JWT_SECRET", "local-development-change-this-key")
SEED_DEMO = os.environ.get("SEED_DEMO", "true").lower() == "true"
