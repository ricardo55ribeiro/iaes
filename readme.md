
## run all comands from the project root

## to install dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## to run the program, use the format
```bash
python proj.py INSTANCE [YYYY-MM-DD] [catboost]
```
(instances are already read from `instances/`; pass the filename only!)

## examples:

Use the original price forecast for a historical day:
```bash
python proj.py historical_day_test.txt 2013-01-01
```

Use CatBoost predictions for the same day:
```bash
python proj.py historical_day_test.txt 2013-01-01 catboost
```

To compare forecasts on a larger example, use `catboost_vs_default_test.txt` with the same commands.

Use manually specified prices:
```bash
python proj.py my_instance.txt
```
(this requires a complete `price_input` list in the instance)


## Output
`schedule` is the start period of each task, in input order
`servers` is the server assigned to each task
`estimated cost` is the total cost using the selected forecast, in €
`on`, `turn_on`, `turn_off` is the server states and switching events
`actual cost` is the cost of the same schedule using actual prices (shown only for historical runs)

Periods start at **0**; server IDs start at **1**.
With 30 minute periods, period 4 is 02:00

## creating instances

Create a text file in `instances/`, with one parameter per line and values
separated by spaces. Use decimal points. Blank lines and comments are
not supported

Example of a complete instance for the current model:

```text
n_tasks             2
n_periods           3
n_servers           1
q                   30
duration            2 1
price_input         0.20 -0.10 0.20
task_power          2.0 2.0
server_idle_power   1000.0
turn_on_cost        0.03
turn_off_cost       0.02
min_start           0 2
max_end             2 3
cpu                 2 1
ram                 2 1
io                  1 2
cpu_c               3
ram_c               4
io_c                3
```


## parameters

`n_tasks`, `n_periods`, `n_servers` - number of tasks, periods and servers
`q` - minutes per period
`duration` - task duration in periods
`price_input` - electricity price per period, in €/kWh
`task_power` - power per task, in kW
`server_idle_power` - idle power per server, in W
`turn_on_cost`, `turn_off_cost` - switching costs per server, in euros
`min_start`, `max_end` - rarliest start and exclusive end limit per task
`cpu`, `ram`, `io` - resource demand per task
`cpu_c`, `ram_c`, `io_c` - resource capacity per server


Additional notes:
- Each task list must contain `n_tasks` values, each server list `n_servers` values, and `price_input` must contain `n_periods` values
- A task must satisfy `start >= min_start` and
`start + duration <= max_end`. Resource demands and capacities must use
consistent units. Changing `q` also changes the real duration of tasks
and time windows.
- `historical_day_test.txt` and
`catboost_vs_default_test.txt` are intended for runs with a date.
`test.txt` uses an older format, and `test_2.txt` has resource-list sizes
that need correcting before use with model 5.

