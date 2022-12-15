from pylauncher import pylauncher
import sys
import os
import glob
import re
from natsort import natsorted

JOB_ID = os.environ.get("SLURM_JOB_ID", "head")
NODEFILE = os.environ.get("PBS_NODEFILE", "head")

# NOTE this line fixes an issue caused by the PACE implementation of pylauncher (I think)
# either way, if you get an error like "Abaqus Error: $PBS_NODEFILE improperly defined.", then this is supposed to fix it
#HOST_HEADER = "HOST=$(/usr/bin/hostname); echo $HOST > node.$HOST; for i in {1..8}; do echo $HOST >> node.$HOST; done; PBS_NODEFILE=$PWD/node.$HOST"

NUM_CORES = 8

inp_dir = sys.argv[1]
# remove trailing slashes
inp_dir = inp_dir.rstrip("/")
print(inp_dir)
jobfile = f"run_abaqus_pylauncher_{JOB_ID}.in"


# get all inps
globstr = f"{inp_dir}/*.inp"
# now filter for solely numeric ones
restr = f"{inp_dir}/[0-9]*.inp"

print(restr, globstr)

# get all numeric inps in directory
all_inps = glob.glob(globstr)
# check that inps are solely numeric
all_inps = filter(re.compile(restr).match, all_inps)
all_inps = natsorted(all_inps)
# all_inps = all_inps[:10]

# TODO: filter out inps that were already run!


print(len(all_inps))
job_lines = "\n".join(
    #f"{HOST_HEADER}; NUM_ABAQUS_CORES={NUM_CORES} bash run_abaqus.sh {inp_name}"
    f"NUM_ABAQUS_CORES={NUM_CORES} bash run_abaqus.sh {inp_name}"
    for inp_name in all_inps
)

# now write job lines to a file
with open(jobfile, "w") as f:
    print(job_lines, file=f)

pylauncher.ClassicLauncher(jobfile, cores=8, debug="job+host+task")
