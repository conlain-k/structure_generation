from odbAccess import *
from abaqusConstants import *
import numpy as np
import sys


# usage 'abaqus cae noGUI=avg_SE_RF.py -- <odb_file_path> <output_file_base>
odb_file = sys.argv[-2]
output_file_base = sys.argv[-1]

odb = openOdb(odb_file)

step = odb.steps["Step-1"]
frame = step.frames[-1]

E_vals = frame.fieldOutputs["E"]
S_vals = frame.fieldOutputs["S"]

# stack so that spatial dims come last
E_arr = np.stack([Ev.data for Ev in E_vals.values], axis=-1)
S_arr = np.stack([Sv.data for Sv in S_vals.values], axis=-1)

print(E_arr.shape)

num_elems = E_arr.shape[-1]
# TODO get the voxel count in a better way
vc = int(round(num_elems ** (1.0 / 3)))

print("Inferred voxel count is", vc)

# 1 instance times 6 components times [x, y, z]
E_arr = E_arr.reshape(1, -1, vc, vc, vc)
S_arr = S_arr.reshape(1, -1, vc, vc, vc)

print("Saving to numpy file base", output_file_base)

strain_file = "{}_strain.npy".format(output_file_base)
stress_file = "{}_stress.npy".format(output_file_base)

np.save(strain_file, E_arr)
np.save(stress_file, S_arr)
