import hashlib,json,random
from sqlalchemy import func
from src.config.database import SessionLocal,Base,engine
from src.models import User,Dataset,Observation,Experiment,AnalysisRun
from src.utils.security import hash_password
from src.services.statistics_service import analyze

def seed():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        for role,name in [("admin","林序 · 实验负责人"),("analyst","许禾 · 数据分析师"),("viewer","周澄 · 产品观察员")]:
            email=role+"@lanqiao.demo"
            if not db.query(User).filter_by(email=email).first(): db.add(User(email=email,name=name,role=role,password_hash=hash_password("Lanqiao2026!")))
        ds=db.query(Dataset).filter_by(name="付费入口 · 11月用户级实验").first()
        if not ds:
            rng=random.Random(42); rows=[]
            for i in range(2400):
                x=max(.1,rng.gauss(36,12)); arm="control" if i%2==0 else "treatment"
                y=max(0,7+.65*x+rng.gauss(0,7)+(2.8 if arm=="treatment" else 0))
                rows.append(dict(subject=f"LQ-{i+1:05}",arm=arm,pre_value=round(x,4),value=round(y,4)))
            ds=Dataset(name="付费入口 · 11月用户级实验",source="lanqiao-paywall-2026-11.csv",description="2400 位独立随机分桶用户；前置7日收入与后置7日收入，合成可复现数据。",checksum=hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest())
            db.add(ds);db.flush()
            db.add_all([Observation(dataset_id=ds.id,**row) for row in rows]);db.flush()
        for name,hyp in [("短文付费入口 v3","以更清晰的阅读价值说明提高每用户7日收入。"),("精选内容预览长度","增加预览长度能提高付费入口收入，需独立新分桶验证。"),("订阅权益说明顺序","将核心权益前置能提高每用户收入，当前复用数据仅作演示。")]:
            if not db.query(Experiment).filter_by(name=name).first():
                exp=Experiment(name=name,dataset_id=ds.id,hypothesis=hyp,owner="许禾 · 数据分析师",alpha=.05,cuped=True)
                db.add(exp);db.flush()
                if name=="短文付费入口 v3":
                    result=analyze(db.query(Observation).filter_by(dataset_id=ds.id).all(),.05,True)
                    db.add(AnalysisRun(experiment_id=exp.id,status="completed",result=result))
        db.commit()
        print(json.dumps({model.__tablename__:db.query(model).count() for model in [User,Dataset,Observation,Experiment,AnalysisRun]},ensure_ascii=False))
if __name__=="__main__": seed()
