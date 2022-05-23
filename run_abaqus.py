#!/usr/bin/env python3
import sys
import os
import subprocess
import numpy as np
import argparse

import h5py

import pathlib

parser = argparse.ArgumentParser(description="Solve linear elasticity via MKS")
parser.add_argument("--inp_dir", required=True, help="Where to read .inp files from")
parser.add_argument("--inp_name", required=True, help="Which inp to run in that dir?")
parser.add_argument(
    "--num_cores", required=True, help="How many cores to run on?", type=int
)
# parser.add_argument("--output_dir", required=True, help="Where to write .dat files to")


# TODO this is hacky
# get current dir to get parser script
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

PARSER_SCR = f"{SCRIPT_DIR}/parseODBToNumpy.py"

OUTPUTS_BASEDIR = "outputs"


def write_results(fname, strain, stress):
    output_f = h5py.File(fname, "w")

    # one chunk for each instance
    chunk_size = (1,) + strain[0].shape
    print("chunk size is", chunk_size)
    print(strain.dtype, strain.shape)
    print(stress.dtype, stress.shape)

    # now make the actual datasets
    output_f.create_dataset(
        "strain",
        data=strain,
        dtype=strain.dtype,
        compression="gzip",
        compression_opts=6,
        chunks=chunk_size,
    )
    output_f.create_dataset(
        "stress",
        data=stress,
        dtype=stress.dtype,
        compression="gzip",
        compression_opts=6,
        chunks=chunk_size,
    )


# suggested by here: https://stackoverflow.com/questions/10840533/most-pythonic-way-to-delete-a-file-which-may-not-exist
def silent_remove(filename):
    try:
        os.remove(filename)
    except OSError:
        pass


def run_cmd(cmd_args):
    print(f"Command string is: {cmd_args}")
    ret = subprocess.Popen(cmd_args).wait()
    print(f"Return code was: {ret}")
    # if we failed, stop now
    if ret != 0:
        raise RuntimeError("Abaqus failed with return code {ret}!")

    return ret


def run_abaqus(jobname, inp_dir, output_dir_abs, num_cores):
    # move to input directory
    os.chdir(inp_dir)

    # set up abaqus command
    ab_cmd = [
        "abaqus",
        f"job={jobname}.inp",
    ] + f"int double interactive cpus={num_cores} ask_delete=off".split(" ")
    run_cmd(ab_cmd)

    # if we haven't failed yet, try and parse
    parse_args = [
        "abaqus",
        "python",
        f"{PARSER_SCR}",
        "--",
        f"{jobname}.odb",
        f"{jobname}",
    ]
    run_cmd(parse_args)

    # Now that we parsed, do some cleanup
    rm_ext = ["msg", "sim", "com", "prt", "odb", "sta", "dat"]
    for ext in rm_ext:
        silent_remove(f"{jobname}.{ext}")

    strain_f = f"{jobname}_strain.npy"
    stress_f = f"{jobname}_stress.npy"

    strain_data = np.load(strain_f)
    stress_data = np.load(stress_f)

    output_file = f"{output_dir_abs}/{jobname}.h5"
    print(f"Saving results for job {jobname} to file {output_file}")
    write_results(output_file, strain_data, stress_data)

    # now cleanup those temp files
    os.remove(strain_f)
    os.remove(stress_f)

    return strain_data, stress_data


def inside_inp_range(inp, start, stop):
    inp = os.path.basename(inp)
    inp_base = os.path.splitext(inp)[0]
    if inp_base.isnumeric():
        inp_num = int(inp_base)
        if inp_num >= start and inp_num < stop:
            return True
    return False


def main():
    args = parser.parse_args()
    # read in args
    inp_dir = pathlib.Path(args.inp_dir).absolute()
    inp_name = args.inp_name

    # now set up target directories
    output_dir = f"{OUTPUTS_BASEDIR}/{os.path.basename(inp_dir)}"
    # get absolute path for when we change directories later
    output_dir_abs = pathlib.Path(output_dir).absolute()

    os.makedirs(OUTPUTS_BASEDIR, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    # rip out extension to make later parsing easier
    jobname = os.path.splitext(os.path.basename(inp_name))[0]
    print(f"Running inp {inp_name} in directory {inp_dir}, jobname is {jobname}!")

    # now actually run things through abaqus
    ret = run_abaqus(jobname, inp_dir, output_dir_abs, num_cores=args.num_cores)

    # all the postprocessing should already be done!

    # E_vals, S_vals
    # ret = np.asarray(ret)
    # print(ret)


if __name__ == "__main__":
    main()
