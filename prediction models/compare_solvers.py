"""Benchmark both solvers on the same integer-cost variant; original model unchanged.
Run: python3 "prediction models/compare_solvers.py"
Requires the official MiniZinc bundle or --minizinc PATH. Writes CSV alongside script.
"""
import argparse, csv, json, re, shutil, subprocess, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser()
parser.add_argument('--minizinc', default=shutil.which('minizinc') or '/Applications/MiniZincIDE.app/Contents/Resources/minizinc')
parser.add_argument('--runs', type=int, default=3)
parser.add_argument('--limit-ms', type=int, default=10000)
a = parser.parse_args()
params = {}
for line in (ROOT/'instances/catboost_vs_default_test.txt').read_text().splitlines():
    key, *values = line.split()
    nums = [float(v) if '.' in v else int(v) for v in values]
    params[key] = nums[0] if key.startswith('n_') or key == 'q' else nums
with (ROOT/'data/Predictions_2013.csv').open() as f:
    day = sorted((r for r in csv.DictReader(f) if r['DateTime'][:10]=='2013-05-01'), key=lambda r:int(r['PeriodOfDay']))
assert len(day)==48
prices = [float(r['CatBoost'])/1000 for r in day]
params['price_input'] = prices
scale = 1000000
hours = params['q']/60
source = (ROOT/'models/model5.mzn').read_text()
# Round each period/event coefficient to the nearest micro-euro, for BOTH solvers.
coeff = [[round(p*hours*f*scale) for f in prices] for p in params['task_power']]
idle = [[round(p/1000*hours*f*scale) for f in prices] for p in params['server_idle_power']]
up = [round(v*scale) for v in params['turn_on_cost']]
down = [round(v*scale) for v in params['turn_off_cost']]
model = source[:source.index('solve minimize')] + '''
array[1..n_tasks,0..n_periods-1] of int: task_cost;
array[1..n_servers,0..n_periods-1] of int: idle_cost;
array[1..n_servers] of int: up_cost;
array[1..n_servers] of int: down_cost;
var int: total_cost =
 sum(j in 1..n_tasks,t in 0..duration[j]-1)(task_cost[j,start[j]+t]) +
 sum(m in 1..n_servers,t in 0..n_periods-1)(bool2int(on[m,t])*idle_cost[m,t] + bool2int(turn_on[m,t])*up_cost[m] + bool2int(turn_off[m,t])*down_cost[m]);
solve minimize total_cost;
output ["AUDIT_START=",show(start),"\\nAUDIT_SERVER=",show(server),"\\nAUDIT_ON=",show([on[m,t] | m in 1..n_servers,t in 0..n_periods-1]),"\\nAUDIT_COST=",show(total_cost),"\\n"];
'''
print(subprocess.check_output([a.minizinc, '--version'], text=True).strip())
print(subprocess.check_output([a.minizinc, '--solvers'], text=True).strip())
rows=[]
with tempfile.TemporaryDirectory(prefix='iaes-solvers-') as tmp:
    tmp=Path(tmp); data=tmp/'input.json'; data.write_text(json.dumps(params))
    for solver in ['gecode','chuffed']:
        result=subprocess.run([a.minizinc,'--solver',solver,'--time-limit','2000',str(ROOT/'models/model5.mzn'),str(data)],capture_output=True,text=True)
        print('Original float model:',solver,'solve exit',result.returncode, result.stderr[-500:])
    data.write_text(json.dumps(dict(params,task_cost=coeff,idle_cost=idle,up_cost=up,down_cost=down)))
    path=tmp/'integer_model.mzn';path.write_text(model)
    for run in range(1,a.runs+1):
        for solver in (['gecode','chuffed'] if run%2 else ['chuffed','gecode']):
            begin=time.perf_counter()
            result=subprocess.run([a.minizinc,'--solver',solver,'--statistics','--time-limit',str(a.limit_ms),str(path),str(data)],capture_output=True,text=True,timeout=a.limit_ms/1000+30)
            wall=time.perf_counter()-begin
            stats=dict(re.findall(r'%%%mzn-stat: (\w+)=(.*)',result.stdout))
            row=dict(solver=solver,run=run,date='2013-05-01',forecast='CatBoost',instance='catboost_vs_default_test.txt',scale=scale,time_limit_ms=a.limit_ms,wall_seconds=wall,flatten_seconds=stats.get('flatTime',''),solve_seconds=stats.get('solveTime',''),status='OPTIMAL' if '==========' in result.stdout else 'FEASIBLE' if 'AUDIT_COST=' in result.stdout else 'ERROR_OR_UNKNOWN',integer_objective='',forecast_cost_eur='',actual_cost_eur='')
            matches=re.findall(r'AUDIT_START=(.*?)\nAUDIT_SERVER=(.*?)\nAUDIT_ON=(.*?)\nAUDIT_COST=(\d+)',result.stdout)
            if matches:
                starts,servers,states,obj=matches[-1]
                starts=json.loads(starts);servers=json.loads(servers);states=json.loads(states)
                energy=[0.0]*48; switch=0.0
                for j,(s,m) in enumerate(zip(starts,servers)):
                    assert params['min_start'][j]<=s and s+params['duration'][j]<=min(params['max_end'][j],48)
                    for t in range(s,s+params['duration'][j]):
                        assert states[(m-1)*48+t]
                        energy[t]+=params['task_power'][j]*hours
                for m in range(2):
                    previous=False
                    for t in range(48):
                        on=states[m*48+t]
                        for resource in ['cpu','ram','io']:
                            assert sum(params[resource][j] for j in range(4) if servers[j]==m+1 and starts[j]<=t<starts[j]+params['duration'][j])<=params[resource+'_c'][m]
                        energy[t]+=on*params['server_idle_power'][m]/1000*hours
                        switch+=(params['turn_on_cost'][m] if on else params['turn_off_cost'][m]) if on!=previous else 0
                        previous=on
                    switch+=previous*params['turn_off_cost'][m]
                cost=sum(e*f for e,f in zip(energy,prices))+switch
                bound=(sum(params['duration'])+3*2*48)*0.5/scale
                assert abs(cost-int(obj)/scale)<=bound+1e-9
                row.update(integer_objective=int(obj),forecast_cost_eur=cost,actual_cost_eur=sum(e*float(r['Actual_SMPEP2'])/1000 for e,r in zip(energy,day))+switch)
            elif result.returncode:
                raise RuntimeError(result.stderr)
            rows.append(row);print(row,flush=True)
out=Path(__file__).with_name('Solver_Comparison.csv')
with out.open('w',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=rows[0]);writer.writeheader();writer.writerows(rows)
print('Saved',out)
