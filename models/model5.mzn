int : n_tasks;
int : n_periods;
int : n_servers;
int: q;                                             % minutes per period

array[1..n_periods] of float: price_input;          % €/kWh
array[0..n_periods-1] of float: price = array1d(0..n_periods-1, price_input);
array[1..n_tasks] of int : duration;
array[1..n_tasks] of float: task_power;             % kW
array[1..n_servers] of float: server_idle_power;    % W
array[1..n_servers] of float: turn_on_cost;         % in €
array[1..n_servers] of float: turn_off_cost;        % in €
array[1..n_tasks] of var 0..n_periods-1: start;
array[1..n_tasks] of var 1..n_servers : server;
array[1..n_tasks] of int : cpu, ram, io;            
array[1..n_tasks] of int : cpu_c, ram_c, io_c;

array[1..n_servers, 0..n_periods-1] of var bool: on;
array[1..n_servers, 0..n_periods-1] of var bool: turn_on;
array[1..n_servers, 0..n_periods-1] of var bool: turn_off;

array[1..n_tasks] of int : min_start;
array[1..n_tasks] of int : max_end;

% to finish tasks within avaliable periods
constraint forall(j in 1..n_tasks)(
    start[j] + duration[j] <= n_periods
);

% tasks on same server shouldnt overlap
%constraint forall(i,j in 1..n_tasks where i<j)(
%    server[i] != server[j] \/ start[i] + duration[i] <= start[j] \/ start[j] + duration[j] <= start[i]
%);
% - now they CAN overlap


% now the constraints we have is on resource capacity (tasks can overlap)
constraint forall(m in 1..n_servers, t in 0..n_periods - 1) (
    sum(j in 1..n_tasks) (
        cpu[j]*bool2int(server[j] == m /\ start[j] <= t /\ t < start[j] + duration[j])
    ) <= cpu_c[m]
    /\
    sum(j in 1..n_tasks) (
        memory[j]*bool2int(server[j] == m /\ start[j] <= t /\ t < start[j] + duration[j])
    ) <= ram_c[m]
    /\
    sum(j in 1..n_tasks) (
        io[j]*bool2int(server[j] == m /\ start[j] <= t /\ t < start[j] + duration[j])
    ) <= io_c[m]
)

% to restrict possible values of sj into the time window
constraint forall(j in 1..n_tasks)(
    start[j] >= min_start[j] /\ start[j] + duration[j] <= max_end[j]
);

% server must be on to execute a task
constraint forall(j in 1..n_tasks, t in start[j]..(start[j] + duration[j] - 1))(
    on[server[j], t]
);

% servers are initially off and must be off after the last period
constraint forall(m in 1..n_servers)(
    turn_on[m,0] = on[m,0] /\ turn_off[m,n_periods-1] = on[m,n_periods-1]
);

% when a server turns on
constraint forall(m in 1..n_servers, t in 1..n_periods-1)(
    turn_on[m,t] = (on[m,t] /\ not on[m,t-1])
);

% when a server turns off
constraint forall(m in 1..n_servers, t in 0..n_periods-2)(
    turn_off[m,t] = (on[m,t] /\ not on[m,t+1])
);


% minimize total cost from task energy + server energy + turn on/off costs
solve minimize
    sum(j in 1..n_tasks)(                                       % task energy cost (2.4.3, Eq. 13):
        sum(t in 0..duration[j]-1)(                             % power (kW) * period duration (hours) * price (€/kWh)
            task_power[j] * (q / 60.0) * price[start[j] + t]
        )
    )
    +                                                           % server energy cost (2.4.3, Eq. 14):
    sum(m in 1..n_servers, t in 0..n_periods-1)(                % power (W) converted to kW * period duration (hours) * price (€/kWh)
        bool2int(on[m,t]) * (server_idle_power[m] / 1000.0) * (q / 60.0) * price[t]
    )
    +
    sum(m in 1..n_servers, t in 0..n_periods-1)(                % turn off/on costs
        bool2int(turn_on[m,t]) * turn_on_cost[m]
        +
        bool2int(turn_off[m,t]) * turn_off_cost[m]
    );
