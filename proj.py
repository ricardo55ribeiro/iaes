import minizinc

model = minizinc.Model("./models/model2.mzn")
solver = minizinc.Solver.lookup("gecode") # in the future we can try using chuffed as well

inst = minizinc.Instance(solver, model)

inst["n_tasks"]     = 4
inst["n_periods"]   = 3
inst["n_servers"]   = 3
inst["duration"]    = [2, 1, 1, 1]  # task 1 takes 2 periods; rest takes 1
inst["price"]       = [5,1,2]

res = inst.solve()

print("schedule = ", res["start"])
print("servers = ", res["server"])
print("cost = ", res.objective)