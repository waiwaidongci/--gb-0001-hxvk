from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from ..models import Experiment, Dataset
from ..utils.serialize import record
from .audit_service import log
def list_experiments(db):
    return [record(x) for x in db.query(Experiment).order_by(Experiment.id.desc())]
def create_experiment(db, data, user):
    if not db.get(Dataset,data.dataset_id): raise HTTPException(404,"数据集不存在")
    if db.query(Experiment).filter_by(name=data.name).first(): raise HTTPException(409,"实验名称已存在")
    row=Experiment(**data.model_dump(), owner=user.name)
    db.add(row); db.flush(); log(db,user.email,"experiment.create",row.id); db.commit()
    return record(row)
