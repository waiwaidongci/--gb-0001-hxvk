"""Welch comparison and pooled CUPED, using scipy's Student t CDF/quantile."""
import numpy as np
from scipy.stats import t

def welch(a,b,alpha):
    if min(len(a),len(b)) < 3: raise ValueError("每组至少需要 3 个独立样本")
    va,vb=float(np.var(a,ddof=1)),float(np.var(b,ddof=1))
    se2=va/len(a)+vb/len(b)
    if se2 <= 1e-14: raise ValueError("组内方差为零，不能执行 Welch 检验")
    se=se2**.5; diff=float(np.mean(b)-np.mean(a))
    df=se2**2/((va/len(a))**2/(len(a)-1)+(vb/len(b))**2/(len(b)-1))
    critical=float(t.ppf(1-alpha/2,df))
    return {"control_mean":float(np.mean(a)),"treatment_mean":float(np.mean(b)),"difference":diff,"standard_error":se,"degrees_of_freedom":df,"p_value":float(2*t.sf(abs(diff/se),df)),"ci_low":diff-critical*se,"ci_high":diff+critical*se,"n_control":len(a),"n_treatment":len(b)}

def analyze(observations, alpha=.05, use_cuped=True):
    if not 0 < alpha < .5: raise ValueError("alpha 必须位于 (0,0.5)")
    if not observations: raise ValueError("数据集为空")
    x=np.array([o.pre_value for o in observations],dtype=float)
    y=np.array([o.value for o in observations],dtype=float)
    arms=np.array([o.arm for o in observations])
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)): raise ValueError("观测含非有限值")
    if not set(arms).issubset({"control","treatment"}): raise ValueError("存在未知实验分组")
    a=arms=="control"; b=arms=="treatment"
    raw=welch(y[a],y[b],alpha)
    theta=0.; adjusted=None; reduction=0.
    if use_cuped:
        vx=float(np.var(x,ddof=1))
        if vx <= 1e-14: raise ValueError("前置指标为常量，CUPED 无法计算")
        theta=float(np.cov(y,x,ddof=1)[0,1]/vx)
        transformed=y-theta*(x-np.mean(x))
        adjusted=welch(transformed[a],transformed[b],alpha)
        reduction=1-adjusted["standard_error"]**2/raw["standard_error"]**2
    chosen=adjusted or raw
    return {"raw":raw,"cuped":adjusted,"theta":theta,"variance_reduction":reduction,"alpha":alpha,"significant":chosen["p_value"]<alpha,"method":"Welch + pooled CUPED" if use_cuped else "Welch","interpretation":"区间完全高于零，可供放量会议审议" if chosen['ci_low']>0 else "证据不足或效果为负，建议保留观察","assumptions":"用户级独立随机分桶；前置变量须在分桶前取得；单一预注册指标，未做多重比较校正"}
