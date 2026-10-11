import minizinc
import sys

model = minizinc.Model("./models/model4.mzn")
solver = minizinc.Solver.lookup("gecode") # in the future we can try using chuffed as well

inst = minizinc.Instance(solver, model)

with open("instances/" + sys.argv[1]) as f:
    for line in f:
        name, *vals = line.split()
        vals = [
            float(v) if "." in v or "e" in v.lower() else int(v)
            for v in vals
        ]
        inst[name] = vals[0] if name.startswith("n_") or name == "q" else vals

res = inst.solve()

print("schedule = ", res["start"])
print("servers = ", res["server"])
print("cost = ", res.objective)

print("on =", res["on"])
print("turn_on =", res["turn_on"])
print("turn_off =", res["turn_off"])