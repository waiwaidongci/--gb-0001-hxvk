from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from ..config.database import Base
class Experiment(Base):
    __tablename__ = "experiments"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"))
    hypothesis: Mapped[str]
    metric: Mapped[str] = mapped_column(default="revenue")
    alpha: Mapped[float] = mapped_column(default=.05)
    cuped: Mapped[bool] = mapped_column(default=True)
    owner: Mapped[str]
