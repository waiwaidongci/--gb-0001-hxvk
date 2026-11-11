from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from ..config.database import Base
from ..utils.clock import now
class Decision(Base):
    __tablename__ = "decisions"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("analysis_runs.id"))
    outcome: Mapped[str]
    note: Mapped[str]
    author: Mapped[str]
    created_at: Mapped[str] = mapped_column(default=now)
