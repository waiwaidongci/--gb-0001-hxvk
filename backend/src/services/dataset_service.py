from fastapi import HTTPException
from sqlalchemy import func
from ..models import Dataset, Observation
from ..utils.serialize import record
def list_datasets(db):
    return [dict(record(d), observations=db.query(Observation).filter_by(dataset_id=d.id).count()) for d in db.query(Dataset).order_by(Dataset.id)]
def observations(db, dataset_id):
    if not db.get(Dataset,dataset_id): raise HTTPException(404,"数据集不存在")
    rows = db.query(Observation).filter_by(dataset_id=dataset_id).order_by(Observation.id).limit(100)
    return [record(x) for x in rows]
