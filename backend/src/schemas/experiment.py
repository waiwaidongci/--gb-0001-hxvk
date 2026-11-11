from pydantic import BaseModel, Field
class ExperimentInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    dataset_id: int
    hypothesis: str = Field(min_length=8, max_length=1000)
    alpha: float = Field(default=.05, gt=0, lt=.5)
    cuped: bool = True
