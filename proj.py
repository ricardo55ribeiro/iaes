import minizinc
import sys
import pandas as pd

model = minizinc.Model("./models/model5.mzn")
solver = minizinc.Solver.lookup("gecode") # in the future we can try using chuffed as well

inst = minizinc.Instance(solver, model)

params = {}

with open("instances/" + sys.argv[1]) as f:
    for line in f:
        name, *vals = line.split()
        if len(sys.argv) > 2 and name == "price_input":
            continue
        vals = [
            float(v) if "." in v or "e" in v.lower() else int(v)
            for v in vals
        ]
        #inst[name] = vals[0] if name.startswith("n_") or name == "q" else vals
        value = vals[0] if name.startswith("n_") or name == "q" else vals
        params[name] = value
        inst[name] = value
    
# load forecast prices for one day
if len(sys.argv) > 2:
    df = pd.read_csv("data/icon_prices_clean.csv")

    day = df[df["DateTime"].str[:10] == sys.argv[2]]
    day = day.sort_values("PeriodOfDay")

    if len(day) != 48:
        raise ValueError("Expected 48 periods for this day")

    selected_prices = day["SMPEA"]

    if len(sys.argv) > 3 and sys.argv[3] == "catboost":
        ml = pd.read_csv("data/Predictions_2013.csv")
        ml_day = ml[ml["DateTime"].str[:10] == sys.argv[2]]
        ml_day = ml_day.sort_values("PeriodOfDay")

        if len(ml_day) != 48 or ml_day["PeriodOfDay"].tolist() != day["PeriodOfDay"].tolist():
            raise ValueError("Missing or mismatched ML predictions for this day")

        selected_prices = ml_day["CatBoost"]

    inst["price_input"] = (selected_prices / 1000).tolist()


res = inst.solve()

print("schedule = ", res["start"])
print("servers = ", res["server"])
print("estimated cost = ", res.objective)

print("on =", res["on"])
print("turn_on =", res["turn_on"])
print("turn_off =", res["turn_off"])


# calculate real cost
if len(sys.argv) > 2:
    forecast = (selected_prices / 1000).tolist()
    actual = (day["SMPEP2"] / 1000).tolist()

    hours = params["q"] / 60
    energy = [0.0] * params["n_periods"]

    for j, start in enumerate(res["start"]):
        for t in range(start, start + params["duration"][j]):
            energy[t] += params["task_power"][j] * hours

    for m, states in enumerate(res["on"]):
        for t, is_on in enumerate(states):
            if is_on:
                energy[t] += params["server_idle_power"][m] / 1000 * hours

    actual_cost = res.objective + sum(
        energy[t] * (actual[t] - forecast[t])
        for t in range(params["n_periods"])
    )

    print("actual cost =", round(actual_cost, 5))