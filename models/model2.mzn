int : n_tasks;
int : n_periods;
int : n_servers;

array[1..n_periods] of int : price;
array[1..n_tasks] of int : duration;
array[1..n_tasks] of var 1..n_periods : start;
array[1..n_tasks] of var 1..n_servers : server;

% to finish tasks within avaliable periods
constraint forall(j in 1..n_tasks) (
    start[j] + duration[j] - 1 <= n_periods
);

% tasks on same server shouldnt overlap
constraint forall(i,j in 1..n_tasks where i<j)(
    server[i] != server[j] \/ start[i] + duration[j] <= start[j] \/ start[j] + duration[j] <= start[i]
);

constraint forall (i,j in 1..n_tasks where i<j)(
    start[i] != start[j] \/ server[i] != server[j]
);

solve minimize sum(j in 1..n_tasks)(
    sum(t in 0..duration[j]-1)(
        price[start[j]+t]
    )
);