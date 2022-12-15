#!/bin/bash
#SBATCH -J abaqus_gen                  		# job name
#SBATCH -N 16 --ntasks-per-node 8 #16          # number of nodes and cores per node required
#SBATCH --mem-per-cpu 8gb                    		# memory per core
#SBATCH --time 20:00:00            	# duration of the job 
#SBATCH -q inferno #hive-nvme-sas #-nvme        # queue name (where job is submitted)
#SBATCH -A gts-skalidindi7-coda20
#SBATCH --mail-type NONE                           # please dont email me
#SBATCH -o slurm_outputs/%j.out    # output file name, may want to change

inp_dir=$1
start_ind=$2
stop_ind=$3

module load abaqus
module load pylauncher
source $SLURM_SUBMIT_DIR/sandbox/bin/activate

cd $SLURM_SUBMIT_DIR

echo $SLURM_JOB_ID
echo $SLURM_JOB_NODELIST


pwd

# first clean the inp directory
bash clean_dir.sh ${inp_dir}

# run abaqus on the given inputs
cmd="python3 launch_gen.py ${inp_dir}"
echo $cmd; $cmd
