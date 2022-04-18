#!/usr/bin/env python3
import sys
import os
import subprocess
import numpy as np
from dask.distributed import Client, LocalCluster
import dask
import glob
import argparse
from natsort import natsorted

import h5py

import pathlib

parser = argparse.ArgumentParser(description="Solve linear elasticity via MKS")
parser.add_argument("--inp_dir", required=True, help="Where to read .inp files from")
# parser.add_argument("--output_dir", required=True, help="Where to write .dat files to")
parser.add_argument(
    "--start_ind",
    default=0,
    type=int,
    help="Which inp file to start with (default zero)",
)
parser.add_argument(
    "--stop_ind",
    default=sys.maxsize,
    type=int,
    help="Which inp file to stop before (exclusive, default is run all)",
)


# TODO this is hacky
# get current dir to get parser script
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

PARSER_SCR = f"{SCRIPT_DIR}/parseODBToNumpy.py"

OUTPUTS_BASEDIR = "outputs"


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
        raise RuntimeError

    return ret


@dask.delayed
def run_abaqus(jobname, inp_dir):
    # move to input directory
    os.chdir(inp_dir)

    # set up abaqus command
    ab_cmd = [
        "abaqus",
        f"job={jobname}.inp",
    ] + "int double interactive cpus=6 ask_delete=off".split(" ")
    run_cmd(ab_cmd)

    # otherwise try and parse
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
    start = args.start_ind
    stop = args.stop_ind
    os.makedirs(OUTPUTS_BASEDIR, exist_ok=True)

    output_filename = f"{OUTPUTS_BASEDIR}/{os.path.basename(inp_dir)}_responses.h5"
    output_filename = pathlib.Path(output_filename).absolute()

    # first get all inp files in the directory
    all_inp = glob.glob(f"{inp_dir}/*.inp")
    all_inp = natsorted(all_inp)

    all_inp = [inp for inp in all_inp if inside_inp_range(inp, start, stop)]

    num_inps = len(all_inp)

    print(all_inp)

    print(f"Running total of {len(all_inp)} .inp files!")

    results = []

    # set up array of dask jobs
    for i_file in all_inp:
        # make sure path is relative
        i_file = os.path.basename(i_file)
        # strip off extension
        jobname = os.path.splitext(i_file)[0]
        res = run_abaqus(jobname, inp_dir)
        results.append(res)

    # now actually compute them
    # E_vals, S_vals
    ret = dask.compute(results, num_workers=1)

    # [instance, stress/strain, component, x, y, z]
    target_shape = (-1, 2, 6) + ret.shape[-3:]
    ret = np.asarray(ret).reshape(target_shape)

    print(ret.shape)

    # split into strain and stress fields for each [instance, component, x, y, z] slice
    E, S = ret[:, 0], ret[:, 1]

    # what shape do we want our fields to be in?
    print("Composite sizes are", E_vals.shape, S_vals.shape)

    print(f"Writing to big file {output_filename}")

    output_f = h5py.File(output_filename, "w")

    chunk_size = (1,) + E_vals.shape[1:]
    print("chunk size is", chunk_size)
    print(E_vals.dtype)
    print(S_vals.dtype)

    output_f.create_dataset(
        "strain",
        data=E_vals,
        chunks=chunk_size,
        dtype=E_vals.dtype,
        compression="gzip",
        compression_opts=6,
        maxshape=(None,) + E_vals.shape[1:],
    )
    output_f.create_dataset(
        "stress",
        data=S_vals,
        chunks=chunk_size,
        dtype=S_vals.dtype,
        compression="gzip",
        compression_opts=6,
        maxshape=(None,) + S_vals.shape[1:],
    )


if __name__ == "__main__":
    main()
