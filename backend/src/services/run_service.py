import csv, io
from fastapi import HTTPException
from redis import Redis
from ..config.settings import REDIS_URL, JOB_QUEUE_KEY
from ..models import AnalysisRun, Experiment
from ..utils.serialize import record
from .audit_service import log
queue=Redis.from_url(REDIS_URL,decode_responses=True)
def list_runs(db):
    return [record(x) for x in db.query(AnalysisRun).order_by(AnalysisRun.id.desc())]
def get_run(db,rid):
    row=db.get(AnalysisRun,rid)
    if not row: raise HTTPException(404,"运行记录不存在")
    return row
def enqueue(db,eid,user):
    if not db.get(Experiment,eid): raise HTTPException(404,"实验不存在")
    row=AnalysisRun(experiment_id=eid,status="queued")
    db.add(row); db.flush(); log(db,user.email,"analysis.enqueue",row.id); db.commit()
    try: queue.rpush(JOB_QUEUE_KEY,row.id)
    except Exception:
        row.status="failed"; row.error="队列不可用，请稍后重新运行"; db.commit(); raise HTTPException(503,row.error)
    return record(row)
def export_run(db,rid):
    row=get_run(db,rid)
    if row.status!="completed": raise HTTPException(409,"运行尚未完成")
    out=io.StringIO(); w=csv.writer(out); w.writerow(["method","n_control","n_treatment","difference","p_value","ci_low","ci_high"])
    for method in ("raw","cuped"):
        result=row.result.get(method)
        if result: w.writerow([method]+[result[k] for k in ["n_control","n_treatment","difference","p_value","ci_low","ci_high"]])
    return out.getvalue()
