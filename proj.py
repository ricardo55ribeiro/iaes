import minizinc

model = minizinc.Model("./models/model1.mzn")
solver = minizinc.Solver.lookup("gecode") # in the future we can try using chuffed as well

inst = minizinc.Instance(solver, model)

inst["n_tasks"]     = 2
inst["n_periods"]   = 3
inst["price"]       = [5,1,2]

res = inst.solve()

print("schedule = ", res["start"])
print("cost = ", res.objective)