int : n_tasks;
int : n_periods;
int : n_servers;

array[1..n_periods] of int : price;
array[1..n_tasks] of int : duration;
array[1..n_tasks] of int: task_energy;
array[1..n_servers] of int: server_energy;
array[1..n_servers] of int: turn_on_cost;  % in €
array[1..n_servers] of int: turn_off_cost; % in €
array[1..n_tasks] of var 1..n_periods : start;
array[1..n_tasks] of var 1..n_servers : server;

array[1..n_servers, 1..n_periods] of var bool: on;
array[1..n_servers, 1..n_periods] of var bool: turn_on;
array[1..n_servers, 1..n_periods] of var bool: turn_off;

array[1..n_tasks] of int : min_start;
array[1..n_tasks] of int : max_end;

% to finish tasks within avaliable periods
constraint forall(j in 1..n_tasks) (
    start[j] + duration[j] - 1 <= n_periods
);

% tasks on same server shouldnt overlap
constraint forall(i,j in 1..n_tasks where i<j)(
    server[i] != server[j] \/ start[i] + duration[i] <= start[j] \/ start[j] + duration[j] <= start[i]
);

constraint forall(j in 1..n_tasks)(
    start[j] >= min_start[j] /\ start[j] + duration[j] - 1 <= max_end[j]
); % to restrict possible values of sj into the time window

% system must be on to execute task
constraint forall(j in 1..n_tasks, t in start[j]..(start[j] + duration[j] - 1))(
    on[server[j], t]
);

% servers are initially off, and have to be off after the last period
constraint forall(m in 1..n_servers)(
    turn_on[m,1] = on[m,1] /\ turn_off[m,n_periods] = on[m,n_periods]
);

% when a server turns on
constraint forall(m in 1..n_servers, t in 2..n_periods)(
    turn_on[m,t] = (on[m,t] /\ not on[m,t-1])
);

% when a server turns off
constraint forall(m in 1..n_servers, t in 1..n_periods-1)(
    turn_off[m,t] = (on[m,t] /\ not on[m,t+1])
);




% minimize total cost from task energy + server energy + turn on/off costs
solve minimize
    sum(j in 1..n_tasks)(
        sum(t in 0..duration[j]-1)(
            task_energy[j] * price[start[j] + t]
        )
    )
    +
    sum(m in 1..n_servers, t in 1..n_periods)(
        bool2int(on[m,t]) * server_energy[m] * price[t]
    )
    +
    sum(m in 1..n_servers, t in 1..n_periods)(
        bool2int(turn_on[m,t]) * turn_on_cost[m]
        +
        bool2int(turn_off[m,t]) * turn_off_cost[m]
    );
