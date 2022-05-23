import pylauncher3
import sys
import os
import glob
import re
from natsort import natsorted

JOB_ID = os.environ.get("PBS_JOBID", "head")

NUM_CORES = 8

inp_dir = sys.argv[1]
jobfile = f"run_abaqus_pylauncher_{JOB_ID}.job"


# get all inps
globstr = f"{inp_dir}/*.inp"
# now filter for solely numeric ones
restr = f"{inp_dir}/[0-9]+.inp"

# get all numeric inps in directory
all_inps = glob.glob(globstr)
# check that inps are solely numeric
all_inps = filter(re.compile(restr).match, all_inps)
all_inps = natsorted(all_inps)
# all_inps = all_inps[:10]

# print(all_inps)
job_lines = "\n".join(
    f"{NUM_CORES}, python3 run_abaqus.py --inp_dir {inp_dir} --inp_name {inp_name} --num_cores {NUM_CORES}"
    for inp_name in all_inps
)

# now write job lines to a file
with open(jobfile, "w") as f:
    print(job_lines, file=f)

# pylauncher3.ClassicLauncher(jobfile, cores="file")
