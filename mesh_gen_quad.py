import numpy as np
from itertools import *
import os
import argparse
import shutil

cwd = os.getcwd()

parser = argparse.ArgumentParser(description='Set domain size for mesh generation')
parser.add_argument('-ds', default=31, type=int, help='set the number of elements for each dimension of the mesh')
parser.add_argument('-e', default=0.001, help='magnitude of the imposed strain')
args = parser.parse_args()
#print(args.ds)

ds = args.ds
applied_strain = args.e

save_dir = os.path.join(cwd,f'quad_mesh_{ds}')

if not os.path.exists(save_dir):
    os.mkdir(save_dir)

#need to copy the pbc file from outside the directory to inside the mesh_ds directory
pbc_file = 'periodic_bc.inp'
pbc_fp = os.path.join(save_dir,pbc_file)
shutil.copy('periodic_bc.inp', pbc_fp)

node_file = f'{ds}_node.inp'
element_file = f'{ds}_element.inp'
nodeset_file = f'{ds}_nodeset.inp'
bc_nset_file = f'{ds}_bc_nset.inp'
step_file = f'{ds}_step.inp'
outputs_file = f'{ds}_outputs.inp'
main_file = f'{ds}_mesh_main.inp'


#comments go here...
#------------- Node File -------------#

x = (ds+1)**3
y = (ds+1)**2
z = (ds+1)

#4 columns - the first one is the node index, the followed three are the XYZ coordinates
arr = list(product(range(ds+1), repeat=3))
arr = np.flip(arr,1)
idx = np.arange(1,x+1)[...,None]
arr = np.concatenate((idx,arr),1)


nodes = []
idx = 0
for k in range(ds+1):
    for j in range(ds+1):
        for i in range(ds):
            idx += 1
            nodes.append([idx,i+1/2, j,k])
            
xarr = np.array(nodes)
yarr = np.copy(xarr)
yarr[:, [1, 2]] = yarr[:, [2, 1]]

nodes = []
idx = 0
for k in range(ds):
    for j in range(ds+1):
        for i in range(ds+1):
            idx += 1
            nodes.append([idx,i, j,k+1/2])

zarr = np.array(nodes)
xarr[:,0] = xarr[:,0] + arr[-1][0]
yarr[:,0] = yarr[:,0] + xarr[-1][0]
zarr[:,0] = zarr[:,0] + yarr[-1][0]

arr = np.concatenate((arr, xarr,yarr,zarr), axis=0)
nodes = np.copy(arr)

arr = np.array(arr.astype('float'),dtype='str')
arr[:,0] = np.char.rstrip(arr[:,0], chars='0')
arr[:,0] = np.char.rstrip(arr[:,0], chars='.')

arr[:,0] = np.char.add(arr[:,0], ',')
arr[:,1] = np.char.add(arr[:,1], ',')
arr[:,2] = np.char.add(arr[:,2], ',')
#arr[:,3] = np.char.add(arr[:,3], '.')


np.savetxt(fname=os.path.join(save_dir, node_file), X=arr, fmt="%s", header="*Node ", comments="")


#------------- Element File -------------#
elements = []
skip = (ds+1)**2
dn = ds + 1
idx = 0
for k in range(ds):
    for j in range(ds):
        for i in range(ds):
            node = k*(dn)**2 + j*(dn) + i + 1
            sub_node = k*(ds*dn) + j*(ds) + i + 1
            snode = k*(ds*dn) + j + i*ds
            idx += 1
            elements.append([idx, 
                skip + node + dn, 
                skip + node, 
                node, 
                node + dn, 
                skip + node + dn + 1, 
                skip + node + 1, 
                node+1, 
                node + dn + 1,

                (dn**2)*ds + dn**3 + dn*ds + snode + 1, #9
                
                dn**3 + 2*ds*(dn**2) + node, #10
                
                (dn**2)*ds + dn**3 + snode + 1, #11
                
                dn**3 + 2*ds*(dn**2) + node + dn, #12
                
                (dn**2)*ds + dn**3 + ds+ dn*ds + snode + 1, #13
                
                dn**3 + 2*ds*(dn**2) + node + 1, #14
                
                (dn**2)*ds + dn**3 + snode + ds + 1, #15
                
                dn**3 + 2*ds*(dn**2) + node + 1 + dn, #16
                
                dn**3 + sub_node+ds + dn*ds, #17
                
                dn**3 + sub_node + dn*ds, #18
                
                dn**3 + sub_node, #19
                
                dn**3 + sub_node+ds, #20
                ])

arr = np.array(elements)

arr = np.array(arr.astype('int'),dtype='str')
for i in range(20):
    arr[:,i] = np.char.add(arr[:,i], ',')
    
head = '*Element, type=C3D20, elset=ALLEL '
np.savetxt(fname=os.path.join(save_dir, element_file), X=arr, fmt="%s", header=head, comments="")

#------------- Node Set File -------------#
base = (ds+1)**2
mid = ((ds+1) * ds ) * 2
main_vec = np.zeros((6,base + mid))

idxy1 = nodes[:, 3] == 0
idxy2 = nodes[:, 3] == ds

idxz1 = nodes[:, 2] == 0
idxz2 = nodes[:, 2] == ds

idyz1 = nodes[:, 1] == 0
idyz2 = nodes[:, 1] == ds

main_vec[0,:] = nodes[idxy1][:, 0]
main_vec[1,:] = nodes[idxy2][:, 0]
main_vec[2,:] = nodes[idxz1][:, 0]
main_vec[3,:] = nodes[idxz2][:, 0]
main_vec[4,:] = nodes[idyz1][:, 0]
main_vec[5,:] = nodes[idyz2][:, 0]


main_vec = main_vec.reshape(6,-1, ds+1)
arr = np.array(main_vec.astype('int'),dtype='str')
for i in range(6):
    arr[i,:] = np.char.add(arr[i,:], ',')

#arr = arr.reshape(6, ds+1, ds+1)
#the indeces are: z1, z2, y1, y2, x1, x2
idx = ['z1', 'z2', 'y1', 'y2', 'x1', 'x2']
header = '*Nset, nset = '
comment = '**'

with open(os.path.join(save_dir,nodeset_file),'w') as f:
    for i in range(6):
        f.write(header + idx[i])
        f.write('\n')
        for j in range(ds+1):
            vals = str(arr[i][j])
            for char in '[]\' ':
                vals = vals.replace(char, '')
            f.write(vals)
        f.write('\n')
        f.write(comment)
        f.write('\n')
f.close()

#------------- Boundary Condition Node Set File -------------#
arr = np.swapaxes(arr, 1, 2)
z1=0
z2=1
y1=2
y2=3
x1=4
x2=5

sxp = nodes[np.logical_and.reduce(
    (nodes[:, 1] == ds, nodes[:, 2]>=.5, 
    nodes[:, 2] <= ds-.5, nodes[:, 3]>=.5, 
    nodes[:, 3] <= ds-.5))][:, 0]

sxm = nodes[np.logical_and.reduce(
    (nodes[:, 1] == 0, nodes[:, 2]>=.5, 
    nodes[:, 2] <= ds-.5, nodes[:, 3]>=.5, 
    nodes[:, 3] <= ds-.5))][:, 0]

szp = nodes[np.logical_and.reduce(
    (nodes[:, 1] >= .5, nodes[:, 1]<=ds-.5, 
    nodes[:, 2] >= .5, nodes[:, 2]<=ds-.5, 
    nodes[:, 3] == ds))][:, 0]

szm = nodes[np.logical_and.reduce(
    (nodes[:, 1] >= .5, nodes[:, 1]<=ds-.5, 
    nodes[:, 2] >= .5, nodes[:, 2]<=ds-.5, 
    nodes[:, 3] == 0))][:, 0]

syp = nodes[np.logical_and.reduce(
    (nodes[:, 1] >= .5, nodes[:, 1]<=ds-.5, 
    nodes[:, 2] == ds, nodes[:, 3]>=.5, 
    nodes[:, 3] <= ds-.5))][:, 0]

sym = nodes[np.logical_and.reduce(
    (nodes[:, 1] >= .5, nodes[:, 1]<=ds-.5, 
    nodes[:, 2] == 0, nodes[:, 3]>=.5, 
    nodes[:, 3] <= ds-.5))][:, 0]

xpyp = nodes[np.logical_and.reduce(
    (nodes[:,1] == ds, nodes[:,2] == ds,
    nodes[:,3] >= .5, nodes[:,3] <= ds-.5
))][:,0]

xpym = nodes[np.logical_and.reduce(
    (nodes[:,1] == ds, nodes[:,2] == 0,
    nodes[:,3] >= .5, nodes[:,3] <= ds-.5 
))][:,0]

xmyp = nodes[np.logical_and.reduce(
    (nodes[:,1] == 0, nodes[:,2] == ds,
    nodes[:,3] >= .5, nodes[:,3] <= ds-.5 
))][:,0]

xmym = nodes[np.logical_and.reduce((
    nodes[:,1] == 0, nodes[:,2] == 0,
    nodes[:,3] >= .5, nodes[:,3] <= ds-.5 
))][:,0]

zpyp = nodes[np.logical_and.reduce((
    nodes[:,1] >= .5, nodes[:,1] <= ds-.5,
    nodes[:,2] == ds, nodes[:,3] == ds
))][:,0]

zpym = nodes[np.logical_and.reduce((
    nodes[:,1] >= .5, nodes[:,1] <= ds-.5,
    nodes[:,2] == 0, nodes[:,3] == ds
))][:,0]

zmyp = nodes[np.logical_and.reduce((
    nodes[:,1] >= .5, nodes[:,1] <= ds-.5,
    nodes[:,2] == ds, nodes[:,3] == 0
))][:,0]

zmym = nodes[np.logical_and.reduce((
    nodes[:,1] >= .5, nodes[:,1] <= ds-.5,
    nodes[:,2] == 0, nodes[:,3] == 0
))][:,0]

zpxp = nodes[np.logical_and.reduce((
    nodes[:,1] == ds, nodes[:,2] >= .5,
    nodes[:,2] <= ds-.5, nodes[:,3] == ds
))][:,0]

zpxm = nodes[np.logical_and.reduce((
    nodes[:,1] == 0, nodes[:,2] >= .5,
    nodes[:,2] <= ds-.5, nodes[:,3] == ds
))][:,0]

zmxp = nodes[np.logical_and.reduce((
    nodes[:,1] == ds, nodes[:,2] >= .5,
    nodes[:,2] <= ds-.5, nodes[:,3] == 0
))][:,0]

zmxm = nodes[np.logical_and.reduce((
    nodes[:,1] == 0, nodes[:,2] >= .5,
    nodes[:,2] <= ds-.5, nodes[:,3] == 0
))][:,0]


c1 = np.array([1])
c2 = np.array([ds+1])
c3 = np.array([(ds+1)**2])
c4 = np.array([ds * (ds + 1) + 1])
c5 = np.array([ds * (ds + 1)**2 + 1])
c6 = np.array([ds * (ds + 1)**2 + ds + 1])
c7 = np.array([(ds + 1)**3])
c8 = np.array([ds * (ds + 1) + 1 + ds * (ds + 1)**2])
node_sets = [
    sxp, sxm, syp, sym, szp, szm, xpyp, xpym, xmyp, xmym, zpyp, 
    zpym, zmyp, zmym, zpxp, zpxm, zmxp, zmxm, c1, c2, c3, c4, 
    c5, c6, c7, c8
    ]

idx = [
    'Set-x+\n', 'Set-x-\n', 'Set-y+\n','Set-y-\n', 'Set-z+\n', 'Set-z-\n', 
    'x+y+\n', 'x+y-\n', 'x-y+\n', 'x-y-\n', 'y+z+\n', 'y-z+\n', 'y+z-\n', 
    'y-z-\n', 'z+x+\n', 'z+x-\n', 'z-x+\n', 'z-x-\n', 'c1\n', 'c2\n', 'c3\n',
    'c4\n', 'c5\n', 'c6\n', 'c7\n', 'c8\n'
    ]
header = '*Nset, nset = '

with open(os.path.join(save_dir,bc_nset_file),'w') as f:
    for i in range(len(idx)):
        f.write(header + idx[i])
        for j in range(node_sets[i].size):
            val = node_sets[i][j].astype('int').astype('str') + ','
            f.write(val)
            if (j+1) % 15 == 0:
                f.write('\n')
        f.write('\n')


#------------- Step File -------------#
displacement = ds * applied_strain

with open(os.path.join(save_dir, step_file), 'w') as f:
    f.write('** ----------------------------------------------------------------\n')
    f.write('** \n')
    f.write('** STEP: Step-1\n')
    f.write('** \n')
    f.write('*Step, name=Step-1\n')
    f.write('*Static\n')
    f.write('0.02, 1., 1e-05, 0.5\n')
    f.write('** \n')
    f.write('** BOUNDARY CONDITIONS\n')
    f.write('** \n')
    f.write('** Name: c1 Type: Displacement/Rotation\n')
    f.write('*Boundary\n')
    f.write('**c1 is origin and should never be changed\n')
    f.write('c1,1,3,0\n')
    f.write('*Boundary\n')
    f.write('** c2 is in the x direction from c1\n')
    f.write('** c4 is in the y direction from c1\n')
    f.write('** c5 is in the z direction from c1\n')
    f.write(f'c2,1,1,{displacement}\n')
    f.write('c5,1,1,0\n')
    f.write('*Boundary\n')
    f.write('c2,2,2,0\n')
    f.write('c4,2,2,0\n')
    f.write('*Boundary\n')
    f.write('c5,3,3,0\n')
    f.write('c4,3,3,0\n')
    f.write('*Boundary\n')
    f.write('c2,3,3,0\n')
    f.write('*Boundary\n')
    f.write('c5,2,2,0\n')
    f.write('*Boundary\n')
    f.write('c4,1,1,0\n')
    f.write('** \n')
    f.write('** OUTPUT REQUESTS\n')
    f.write('**\n')
    f.write('*output, field, frequency=1\n')
    f.write('*ELEMENT OUTPUT, POSITION=CENTROIDAL, ELSET=ALLEL\n')
    f.write('S\n')
    f.write('E\n')
    f.write('**\n')
    f.write('*output, history, frequency=0\n')
    f.write('** \n')
    f.write('*el print, summary=yes, totals=yes, position=centroidal\n')
    f.write('S\n')
    f.write('E\n')
    f.write('**\n')
    f.write('*End Step\n')
f.close()

#------------- Main File -------------#

with open(os.path.join(save_dir, main_file),'w') as f:
    f.write('*INCLUDE, INPUT=' + os.path.join(save_dir, node_file) + '\n')
    f.write('*INCLUDE, INPUT=' + os.path.join(save_dir, element_file) + '\n')
    #f.write('*INCLUDE, INPUT=' + os.path.join(save_dir, nodeset_file) + '\n')
    f.write('*INCLUDE, INPUT=' + os.path.join(save_dir, bc_nset_file) + '\n')
    f.write('*INCLUDE, INPUT=' + os.path.join(save_dir, pbc_file) + '\n')
    f.write('*INCLUDE, INPUT=' + os.path.join(save_dir, step_file) + '\n')

f.close()