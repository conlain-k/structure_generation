#!/bin/bash

# make sure abaqus is actually loaded
module load abaqus 

### Run a given input file through abaqus, parse its output, and then convert its output to h5

# if the number of cores isn't in our env, default to 8
if [[ -z "${NUM_ABAQUS_CORES}" ]]; then
  NUM_ABAQUS_CORES=8 # default to 8 cores
fi

# get absolute path to parser script (assumes this script is in the current directory)
ODB_PARSER_SCRIPT=$(realpath parseODBToNumpy.py)
COLLECT_SCRIPT=$(realpath manage_data.py)

# jobname is first and only input
inp_file="$1"

# get the job directory and name from the inp file
jobdir=$(dirname $inp_file)
jobname=$(basename $inp_file .inp)
# what name is this group of files?
groupname=$(basename $jobdir)

# assume the output dir is in this directory, make sure it exists
output_dir=$(realpath outputs/${groupname})
mkdir -p $output_dir

echo outputdir, $output_dir

# go to the job directory (but keep our current location in a stack)
pushd $jobdir

# first run through abaqus
abaqus_cmd="abaqus job=${jobname}.inp int double interactive cpus=${NUM_ABAQUS_CORES} ask_delete=off"

echo $abaqus_cmd
eval $abaqus_cmd
echo Result was $? # how did we do?

# now parse with abaqus
parse_cmd="abaqus python ${ODB_PARSER_SCRIPT} -- ${jobname}.odb"

echo $parse_cmd
eval $parse_cmd
echo Result was $? # how did we do?

# remove temp files now that we are parsed
rm -rf ${jobname}.msg ${jobname}.sim ${jobname}.com ${jobname}.prt ${jobname}.odb ${jobname}.sta ${jobname}.dat ${jobname}.lck


# now collect data into single file
collect_cmd="python3 ${COLLECT_SCRIPT} --collect_fields ${output_dir}/${jobname}.h5 ${jobname}_strain.npy ${jobname}_stress.npy"
echo $collect_cmd
eval $collect_cmd
echo Result was $? # how did we do?

# and now we're done! Just need to collect data 

