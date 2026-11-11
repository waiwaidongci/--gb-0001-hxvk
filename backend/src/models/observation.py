from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from ..config.database import Base
class Observation(Base):
    __tablename__ = "observations"
    __table_args__ = (UniqueConstraint("dataset_id", "subject"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"))
    subject: Mapped[str]
    arm: Mapped[str]
    pre_value: Mapped[float]
    value: Mapped[float]
