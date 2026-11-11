from pydantic import BaseModel
class DatasetSummary(BaseModel):
    id: int
    name: str
    source: str
    description: str
    checksum: str
    observations: int
class ObservationRow(BaseModel):
    subject: str
    arm: str
    pre_value: float
    value: float
