from fastapi import HTTPException
from ..models import Decision, AnalysisRun
from ..utils.serialize import record
from .audit_service import log
def list_decisions(db):
    return [record(x) for x in db.query(Decision).order_by(Decision.id.desc())]
def create_decision(db,data,user):
    run=db.get(AnalysisRun,data.run_id)
    if not run or run.status!="completed": raise HTTPException(409,"只能审议已完成分析")
    row=Decision(**data.model_dump(),author=user.name)
    db.add(row); db.flush(); log(db,user.email,"decision."+data.outcome,row.id); db.commit()
    return record(row)
