import sys
import os
import numpy as np
import h5py
import argparse

parser = argparse.ArgumentParser(description="Solve linear elasticity via MKS")
parser.add_argument('--inp_dir', nargs=1, required=True, help='Where to write .inp files to')
parser.add_argument('--micro_file', nargs=1, required=True, help='What microstructure file to read in')
parser.add_argument('--contrast_ratio', nargs=1, required=True, help='What contrast ratio to write out')
parser.add_argument('--voxel_size', nargs=1, required=True, help='What voxel width (i.e. k for a k x k x k microstructure) to write out')

reverse = False

allow_skip = False

stiffnessLow = 100


def make_matstr(cr):
    base_str = '''**** ----------------------------------------------------------------- 
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
'''

    stiffnessHigh = cr * stiffnessLow

    return base_str.format(stiffnessLow, stiffnessHigh)


def write_inp(mh, fname, ds=31, cr=2, metadata=None):
    if os.path.exists(fname):
        if allow_skip:
            print("File {} exists, skipping!".format(fname))
            return
        else:
            with open(fname, 'w') as f:
                pass  # truncate file first
    ostr = ''

    metadata_str = f'***METADATA is:{metadata}'

    matstr = make_matstr(float(cr))

    mesh_main = f'mesh_{ds}/{ds}_mesh_main.inp'

    # add material definitions and then copy mesh headers
    with open(fname, 'w') as f:
        with open(mesh_main, 'r') as fm:
            tmp = fm.read()
#        f.write(metadata_str)
        f.write(matstr)
        f.write(tmp)

    mf = mh.ravel()

    # add one because elements are one-based in abaqus
    m1 = np.isclose(mf, 0).nonzero()[0] + 1
    m2 = np.isclose(mf, 1).nonzero()[0] + 1

    # is the first phase high or low?
    if reverse:
        tmp = m1
        m1 = m2
        m2 = tmp

    from time import sleep

    def arr_to_str(arr):
        # make lines
        spl = [','.join(str(a) for a in arr[i:i+10]) for i in range(0, arr.size, 10)]
        lines = '\n'.join(spl)
        sleep(0.1)
        return lines

    # soft material set
    ostr += '**\n*Elset, elset=Set-soft\n'
    ostr += arr_to_str(m1)
    ostr += '\n**\n*Elset, elset=Set-hard\n'
    ostr += arr_to_str(m2)
    ostr += '\n'

    # print(fname)
    # append to main file
    with open(fname, 'a') as f:
        f.write(ostr)


def micro_to_inp(micro_file, inp_dir, contrast_ratio, voxel_size):
    micro_data = h5py.File(micro_file, 'r')
    micros = micro_data['micros']
  #  metadata = micro_data['metadata']
    if micros.ndim == 3:
        # make sure we have a 4d input for loop below
        micros = micros[np.newaxis, :]
    elif micros.ndim == 4:
        pass # this is good
    else:
        assert "Error! Data has wrong size!!!"
    
    print(micros.shape)

    # get base name of micro file (strip out directory)
    micro_base = os.path.basename(micro_file)
    # now strip out extension
    inp_base = os.path.splitext(micro_base)[0]

    job_name_base = f"{inp_base}_c{contrast_ratio}"

    os.makedirs(inp_dir, exist_ok=True)

    for i, m in enumerate(micros[:]):
        # where to write inp file?
        inp_name = f"{inp_dir}/{inp_base}_{contrast_ratio}_{i}.inp"
        print(f"Converting {inp_name}")
        write_inp(m, inp_name, ds=voxel_size, cr=contrast_ratio)


if __name__ == "__main__":
    args = parser.parse_args()
    # read in args
    inp_dir = args.inp_dir[0]
    micro_file = args.micro_file[0]
    contrast_ratio = int(args.contrast_ratio[0])
    voxel_size = int(args.voxel_size[0])
    

    micro_to_inp(micro_file, inp_dir, contrast_ratio, voxel_size)
