#!/usr/bin/env python3
import sys
import os
import numpy as np
import h5py
import argparse


from mesh_gen import generate_abaqus_mesh


parser = argparse.ArgumentParser(
    description="Convert a set of microstructures into a directory full of inp files"
)
parser.add_argument(
    "--micro_file", required=True, help="What microstructure file to read in"
)
parser.add_argument(
    "--contrast_ratio",
    default=10,
    required=True,
    type=int,
    help="What contrast ratio to write out",
)
parser.add_argument(
    "--ds",
    default=31,
    type=int,
    help="Set the number of elements for each dimension of the mesh",
)

parser.add_argument(
    "--bc_component",
    default=0,
    type=int,
    choices=[0, 1, 2, 3, 4, 5],
    help="Which direction should we strain for the appplied BCs (in Abaqus ordering)?",
)
parser.add_argument(
    "--applied_strain",
    default=0.001,
    type=float,
    help="Magnitude of the imposed strain",
)

allow_skip = True

stiffnessLow = 100

INP_BASEDIR = "inputs"


# base string to fill in with our contrast params
mat_base_str = """**** ----------------------------------------------------------------- 
** MATERIALS
**
*Solid Section, elset=Set-soft, material=material-1
1.,
*Material, name=material-1
*Elastic,type=isotropic
{}, 0.3
** Solid (element 2 = Set-hard)
**
*Solid Section, elset=Set-hard, material=material-2
1.,
**
*Material, name=material-2
*Elastic,type=isotropic
{}, 0.3
**
"""


def make_matstr(cr):
    stiffnessHigh = cr * stiffnessLow

    return mat_base_str.format(stiffnessLow, stiffnessHigh)


def make_elsetstr(micro):
    """convert a microstructure into a set of element phase assignments in string form"""
    mf = micro.ravel()

    # add one because elements are one-based in abaqus
    m1 = np.isclose(mf, 0).nonzero()[0] + 1
    m2 = np.isclose(mf, 1).nonzero()[0] + 1

    # # is the first phase high or low?
    # if reverse:
    #     tmp = m1
    #     m1 = m2
    #     m2 = tmp

    from time import sleep

    def arr_to_str(arr):
        # make lines, 10 entries per line to keep it legible
        spl = [
            ",".join(str(a) for a in arr[i : i + 10]) for i in range(0, arr.size, 10)
        ]
        lines = "\n".join(spl)
        # sleep(0.1)
        return lines

    # soft material set
    elset_str = ""
    elset_str += "**\n*Elset, elset=Set-soft\n"
    elset_str += arr_to_str(m1)
    elset_str += "\n**\n*Elset, elset=Set-hard\n"
    elset_str += arr_to_str(m2)
    elset_str += "\n"

    return elset_str


def write_inp(micro, inp_name, matstr, mesh_main_file):
    """Write a single microstructure to an inp file"""
    # if the file exists, consider not duplicating it
    if os.path.exists(inp_name):
        # are we allowed to skip it?
        if allow_skip:
            print("File {} exists, skipping!".format(inp_name))
            return
        else:
            with open(inp_name, "w") as f:
                pass  # truncate file first

    elset_str = make_elsetstr(micro)

    # pull in main mesh data
    with open(mesh_main_file, "r") as fm:
        mesh_main_str = fm.read()

    # add material definitions and then copy mesh headers
    with open(inp_name, "w") as f:
        # first write material params
        f.write(matstr)

        # now copy mesh main data
        f.write(mesh_main_str)

        # finally copy element set
        f.write(elset_str)


def main():
    args = parser.parse_args()

    # read in args
    micro_file = args.micro_file
    bc_component = args.bc_component
    contrast_ratio = args.contrast_ratio
    applied_strain = float(args.applied_strain)
    voxel_size = int(args.ds)

    """Convert a set of microstructures into a directory full of inp files"""
    micro_data = h5py.File(micro_file, "r")
    micros = micro_data["micros"]
    #  metadata = micro_data['metadata']
    if micros.ndim == 3:
        # make sure we have a 4d input for loop below
        micros = micros[np.newaxis, :]
    elif micros.ndim == 4:
        pass  # this is good
    else:
        assert "Error! Data has wrong size!!!"

    print(micros.shape)

    # get base name of micro file (strip out directory)
    micro_base = os.path.basename(micro_file)
    # now strip out extension
    inp_base = os.path.splitext(micro_base)[0]

    # does our directory end in "_micros" ?
    if inp_base.split("_")[-1].lower() == "micros":
        # cut off "_micros" if we can
        inp_base = inp_base[:-7]

    inps_dir = f"{INP_BASEDIR}/{inp_base}_cr{contrast_ratio}_bc{bc_component}"

    os.makedirs(INP_BASEDIR, exist_ok=True)
    os.makedirs(inps_dir, exist_ok=True)

    # now generate an abaqus mesh
    print("Generating abaqus mesh!")
    mesh_main_file = generate_abaqus_mesh(
        ds=voxel_size,
        applied_strain=applied_strain,
        bc_component=bc_component,
        save_dir=inps_dir,
    )

    # make material params string
    matstr = make_matstr(float(contrast_ratio))

    for i, m in enumerate(micros[:]):
        # where to write inp file?
        inp_name = f"{inps_dir}/{i:05}.inp"
        print(f"Writing out {inp_name}")
        write_inp(m, inp_name, matstr=matstr, mesh_main_file=mesh_main_file)


if __name__ == "__main__":
    main()
