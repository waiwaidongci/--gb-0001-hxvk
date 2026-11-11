from pydantic import BaseModel
class RunOutput(BaseModel):
    id: int
    experiment_id: int
    status: str
    result: dict
    error: str
    created_at: str
