from typing import Literal
from pydantic import BaseModel, Field
class DecisionInput(BaseModel):
    run_id: int
    outcome: Literal["ship", "hold", "reject"]
    note: str = Field(min_length=8, max_length=2000)
