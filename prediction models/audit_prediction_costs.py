"""Reproduce the report's small-instance scheduling comparison.

Run: python3 "prediction models/audit_prediction_costs.py"
Requires NumPy and pandas. Reads data/Predictions_2013.csv and writes
Scheduling_Cost_Comparison.csv beside this script. The four-task, two-server
instance is hard-coded, as in the original audit of 2026-10-15. Predictors
are not retrained. Actual_SMPEP2 is the perfect-information reference.
"""
from pathlib import Path
import numpy as np,pandas as pd,time

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = Path(__file__).resolve().parent / "Scheduling_Cost_Comparison.csv"
from itertools import product
st=time.time();z=np.array(list(product(range(4,11),range(4,12),range(24,31),range(24,32),range(2),range(2),range(2),range(2))))
s=z[:,:4];a=z[:,4:];dur=np.array([2,1,2,1]);pw=np.array([2,1.2,3,1.8]);t=np.arange(48);act=(s[:,:,None]<=t)&(t<s[:,:,None]+dur[None,:,None]);valid=np.ones(len(s),bool);req=[]
for m in range(2):
 on=act&(a[:,:,None]==m);req.append(on.any(axis=1))
 for res,cap in [(np.array([30,20,35,15]),[45,70]),(np.array([24,16,28,12]),[48,64]),(np.array([12,10,15,8]),[20,32])]:valid&=((on*res[None,:,None]).sum(axis=1)<=cap[m]).all(axis=1)
s=s[valid];a=a[valid];req=np.array(req)[:,valid];energy=(act*pw[None,:,None]*.5).sum(axis=1)[valid];up=[.03,.05];down=[.02,.03];idle=np.array([.350,.750])*.5

def solve(prices,real):
 costs=(energy*prices).sum(axis=1)
 for m in range(2):
  off=np.zeros(len(s));on=np.full(len(s),np.inf)
  for tt in range(48):
   noff=np.minimum(off,on+down[m]);non=np.minimum(on,off+up[m])+idle[m]*prices[tt];noff[req[m,:,tt]]=np.inf;off,on=noff,non
  costs+=np.minimum(off,on+down[m])
 k=np.flatnonzero(costs<=costs.min()+1e-12)[0];en=energy[k].copy();switch=0
 for m in range(2):
  d=np.array([0.,np.inf]);hist=[]
  for tt in range(48):
   tr=np.array([[d[0],d[1]+down[m]],[d[0]+up[m],d[1]]]);prev=tr.argmin(axis=1);v=tr.min(axis=1);v[1]+=idle[m]*prices[tt]
   if req[m,k,tt]:v[0]=np.inf
   hist.append(prev);d=v
  state=int(d[1]+down[m]<d[0]);switch+=state*down[m]
  for tt in range(47,-1,-1):
   en[tt]+=state*idle[m];ps=int(hist[tt][state]);switch+=(up[m] if state else down[m]) if ps!=state else 0;state=ps
 assert abs(en@prices+switch-costs[k])<1e-9
 return float(en@real+switch)
p=pd.read_csv(ROOT / 'data' / 'Predictions_2013.csv');cols=['Original_SMPEA','HistGradientBoosting','LightGBM','CatBoost','XGBoost','Lasso','Actual_SMPEP2'];rows=[]
for date,d in p.groupby(p.DateTime.str[:10]):
 d=d.sort_values('PeriodOfDay');real=d.Actual_SMPEP2.to_numpy()/1000;rows.append([solve(d[c].to_numpy()/1000,real) for c in cols])
r=np.array(rows);print('days',len(r),'feasible schedules per day',len(s),'seconds',time.time()-st)
for i,c in enumerate(cols):
 delta=r[:,0]-r[:,i];print(c,'total',r[:,i].sum(),'saving_pct',delta.sum()/r[:,0].sum()*100,'win_loss_tie',sum(delta>1e-9),sum(delta< -1e-9),sum(abs(delta)<=1e-9),'regret',sum(r[:,i]-r[:,-1]))
delta=r[:,0]-r[:,3];rng=np.random.default_rng(42);starts=rng.integers(0,len(r),size=(5000,52));idx=(starts[:,:,None]+np.arange(7))%len(r);sums=delta[idx.reshape(5000,-1)].sum(axis=1);print('CatBoost saving bootstrap 95%',np.quantile(sums,[.025,.975]));print('largest daily saving/loss',delta.max(),delta.min())

# MAE uses the original euro/MWh values; scheduling costs are in euros.
comparison = []
for i, name in enumerate(cols):
    delta = r[:, 0] - r[:, i]
    comparison.append({
        "model": name,
        "days": len(r),
        "mae_eur_per_mwh": float((p[name] - p["Actual_SMPEP2"]).abs().mean()) if name != "Actual_SMPEP2" else np.nan,
        "realised_cost_eur": float(r[:, i].sum()),
        "saving_eur": float(delta.sum()),
        "saving_pct": float(delta.sum() / r[:, 0].sum() * 100),
        "wins": int((delta > 1e-9).sum()),
        "losses": int((delta < -1e-9).sum()),
        "ties": int((abs(delta) <= 1e-9).sum()),
        "regret_eur": float((r[:, i] - r[:, -1]).sum()),
    })
pd.DataFrame(comparison).to_csv(OUTPUT, index=False)
print(f"Comparison saved to {OUTPUT}")
