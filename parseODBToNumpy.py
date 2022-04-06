from odbAccess import *
from abaqusConstants import *
import numpy as np
import os, sys


# usage 'abaqus cae noGUI=avg_SE_RF.py -- <odb_file_path> <output_file_base>
odb_file = sys.argv[-2]
output_file_base = sys.argv[-1]

odb = openOdb(odb_file)

step = odb.steps['Step-1']
frame = step.frames[-1]

E_vals = frame.fieldOutputs['E']
S_vals = frame.fieldOutputs['S']

# stack so that spatial dims come last
E_arr = np.stack([Ev.data for Ev in E_vals.values], axis=-1)
S_arr = np.stack([Sv.data for Sv in S_vals.values], axis=-1)

print(E_arr.shape)

num_elems = E_arr.shape[-1]
# TODO get the voxel count in a better way
vc = int(round(num_elems**(1./3)))

print("Inferred voxel count is", vc)

E_arr = E_arr.reshape(-1, vc, vc, vc)
S_arr = S_arr.reshape(-1, vc, vc, vc)

print(E_arr.shape)
print(S_arr.shape)

all_U = np.zeros((len(step.frames), 3, (vc+1)**3))
for i in range(len(step.frames) - 1):
    frame = step.frames[i+1]
    U = frame.fieldOutputs['U']
    U_arr = np.stack([Uv.data for Uv in U.values], axis=-1)
    all_U[i,...] = U_arr

all_U = all_U.reshape(-1, 3, vc+1,vc+1,vc+1)
print(all_U.shape)

print('Saving to file base', output_file_base)

strain_file = '{}_strain.npy'.format(output_file_base)
stress_file = '{}_stress.npy'.format(output_file_base)
disp_file = '{}_displacement.npy'.format(output_file_base)

np.save(strain_file, E_arr)
np.save(stress_file, S_arr)
np.save(disp_file, all_U)
