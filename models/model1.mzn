int : n_tasks;
int : n_periods;

array[1..n_periods] of int : price;
array[1..n_tasks] of var 1..n_periods : start;

constraint forall (i,j in 1..n_tasks where i<j)(
    start[i] != start[j]
);

solve minimize sum(j in 1..n_tasks)(price[start[j]]);