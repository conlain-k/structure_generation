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
parser.add_argument(
    "--inp_dir", nargs=1, required=True, help="Where to read .inp files from"
)
parser.add_argument(
    "--output_dir", nargs=1, required=True, help="Where to write .dat files to"
)
parser.add_argument(
    "--voxel_count", nargs=1, required=False, help="How many voxels in each direction?"
)


# TODO this is hacky
# get current dir to get parser script
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

PARSER_SCR = f"{SCRIPT_DIR}/parseODBToNumpy.py"


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


def run_abaqus(jobname, inp_dir, output_dir):
    # keep current directory for later
    cwd = os.getcwd()
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
    displacement_f = f"{jobname}_displacement.npy"

    strain_data = np.load(strain_f)
    stress_data = np.load(stress_f)
    displacement_data = np.load(displacement_f)

    # now cleanup those temp files
    os.remove(strain_f)
    os.remove(stress_f)
    os.remove(displacement_f)

    return strain_data, stress_data, displacement_data


@dask.delayed
def run_abaqus_dask(jobname, inp_dir, output_dir):
    return run_abaqus(jobname, inp_dir, output_dir)


def run_all_abaqus(inp_dir, output_dir, voxel_count=None):
    all_inp = glob.glob(f"{inp_dir}/*.inp")
    all_inp = natsorted(all_inp)

    print(f"Running total of {len(all_inp)} .inp files!")

    results = []

    # set up array of dask jobs
    for i_file in all_inp:
        # make sure path is relative
        i_file = os.path.basename(i_file)
        # strip off extension
        jobname = os.path.splitext(i_file)[0]
        res = run_abaqus_dask(jobname, inp_dir, output_dir)
        results.append(res)

    # now actually compute them
    # E_vals, S_vals
    ret = dask.compute(results, num_workers=1)

    E, S, U = ret[0:2], ret[2:4], ret[4:6]
    E_vals = np.asarray(E).squeeze()
    S_vals = np.asarray(S).squeeze()
    U_vals = np.asarray(U).squeeze()

    # data = np.asarray(ret)

    # print(data.shape)

    # dask added some extra dims that we should get rid of
    # data = data.squeeze(axis=(0))

    # E_vals, S_vals, U_vals = data[:, 0], data[:, 1], data[:,2]

    print("Composite sizes are", E_vals.shape, S_vals.shape, U_vals.shape)

    output_filename = f"{output_dir}/{os.path.basename(inp_dir)}_responses.h5"

    print(f"Writing to big file {output_filename}")

    output_f = h5py.File(output_filename, "w")

    chunk_size = (1,) + E_vals.shape[1:]
    print("chunk size is", chunk_size)
    print(E_vals.dtype)
    print(S_vals.dtype)
    print(U_vals.dtype)

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
    output_f.create_dataset(
        "displacement",
        data=U_vals,
        chunks=chunk_size,
        dtype=U_vals.dtype,
        compression="gzip",
        compression_opts=6,
        maxshape=(None,) + U_vals.shape[1:],
    )


if __name__ == "__main__":
    args = parser.parse_args()
    # read in args
    inp_dir = pathlib.Path(args.inp_dir[0]).absolute()
    output_dir = pathlib.Path(args.output_dir[0]).absolute()
    os.makedirs(output_dir, exist_ok=True)

    vc = None
    if args.voxel_count:
        vc = int(args.voxel_count[0])

    run_all_abaqus(inp_dir, output_dir, vc)
