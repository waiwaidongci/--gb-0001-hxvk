from sqlalchemy import ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from ..config.database import Base
from ..utils.clock import now
class AnalysisRun(Base):
    __tablename__ = "analysis_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id"))
    status: Mapped[str] = mapped_column(default="queued")
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str] = mapped_column(default="")
    # 租约：worker 领取任务时写入自身标识与时间戳，心跳续租；进程中断后租约到期可被其他 worker 接手
    locked_by: Mapped[str] = mapped_column(default="")
    locked_at: Mapped[str] = mapped_column(default="")
    # 已领取次数，每次原子领取 +1，超过上限不再自动重试
    attempts: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[str] = mapped_column(default=now)
