from sqlalchemy.orm import Mapped, mapped_column
from ..config.database import Base
class Dataset(Base):
    __tablename__ = "datasets"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    source: Mapped[str]
    description: Mapped[str]
    checksum: Mapped[str]
