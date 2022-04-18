#!/usr/bin/bash

# taken from SO: https://stackoverflow.com/questions/2394988/get-ceiling-integer-from-number-in-linux-bash
ceildiv(){ echo $((($1+$2-1)/$2)); }
count_inps(){ echo $(find ${inp_dir} -regex "${inp_dir}/[0-9]+\.inp" | wc -l); }

# where to look for inp files
inp_dir=$1

echo $inp_dir

num_inps=$(count_inps $inp_dir)
echo $num_inps

# how many inps per batch?
num_per_batch=200

num_batch=$(ceildiv $num_inps $num_per_batch)

echo "num_batch", $num_batch

# now loop over all batches and submit to the cluster
for ((batch=1; batch<=$num_batch; batch++))
do
    lo=$(($batch * $num_per_batch + 1))
    hi=$(($lo + $num_per_batch))
    cmd="qsub run_abaqus_micros.pbs -F '${inp_dir} ${lo} ${hi}'"
    echo $cmd
    eval $cmd 
    sleep 0.1
done


