import numpy as np
from itertools import *
import os
import argparse
import shutil

cwd = os.getcwd()

parser = argparse.ArgumentParser(description="Set domain size for mesh generation")
parser.add_argument(
    "-ds",
    default=31,
    type=int,
    help="Set the number of elements for each dimension of the mesh",
)
parser.add_argument(
    "-bc_component",
    default=0,
    type=int,
    choices=[0, 1, 2, 3, 4, 5],
    help="Which direction should we strain for the appplied BCs (in Abaqus ordering)?",
)
parser.add_argument("-e", default=0.001, help="Magnitude of the imposed strain")


def generate_abaqus_mesh(ds, applied_strain, bc_component, save_dir=None):
    if save_dir is None:
        # default to a subdirectory of the current one
        save_dir = os.path.join(cwd, f"mesh_{ds}")

    if not os.path.exists(save_dir):
        os.mkdir(save_dir)
    # need to copy the pbc file from outside the directory to inside the mesh_ds directory
    pbc_file = "periodic_bc.inp"
    pbc_fp = os.path.join(save_dir, pbc_file)
    shutil.copy("periodic_bc.inp", pbc_fp)

    node_file = f"{ds}_node.inp"
    element_file = f"{ds}_element.inp"
    nodeset_file = f"{ds}_nodeset.inp"
    bc_nset_file = f"{ds}_bc_nset.inp"
    step_file = f"{ds}_step.inp"
    outputs_file = f"{ds}_outputs.inp"
    main_file = f"{ds}_mesh_main.inp"

    # comments go here...
    # ------------- Node File -------------#

    x = (ds + 1) ** 3
    y = (ds + 1) ** 2
    z = ds + 1

    # 4 columns - the first one is the node index, the followed three are the XYZ coordinates
    arr = list(product(range(ds + 1), repeat=3))
    arr = np.flip(arr, 1)
    idx = np.arange(1, x + 1)[..., None]
    arr = np.concatenate((idx, arr), 1)
    arr = np.array(arr.astype("int"), dtype="str")

    arr[:, 0] = np.char.add(arr[:, 0], ",")
    arr[:, 1] = np.char.add(arr[:, 1], ".,")
    arr[:, 2] = np.char.add(arr[:, 2], ".,")
    arr[:, 3] = np.char.add(arr[:, 3], ".")

    np.savetxt(
        fname=os.path.join(save_dir, node_file),
        X=arr,
        fmt="%s",
        header="*Node ",
        comments="",
    )

    # ------------- Element File -------------#
    """
    x = (ds+1)**2 + ds+2
    y = ds**2
    z = ds**3

    arr = np.zeros((z,8),dtype='int')
    idx = np.arange(1,z+1)[...,None]
    arr = np.concatenate((idx,arr), 1)

    #setting initial node assignments - the remaining elements are based on this assignment
    arr[0,1] = x
    arr[0,2] = x - (ds + 1)
    arr[0,3] = 1
    arr[0,4] = 2 + ds
    arr[0,5] = x + 1
    arr[0,6] = x - ds
    arr[0,7] = 2
    arr[0,8] = 3 + ds

    a = 1
    b = 2
    #these iterate through each ds^3 elements. The node numbers are specified in indices 1-8
    for f in range(1,9):
        for i in range(ds-1):
            arr[i+1,f] = arr[i,f] + a
        for i in range(0,(ds**3)-ds,ds):
            arr[i+ds, f] = arr[i+ds-1,f] + b
            for j in range(ds-1):
                #j = j-1
                arr[i+ds+1+j, f] = arr[i+ds+j,f] + 1
        #not entirely sure what this does?
        for j in range(ds-1):
            for i in range(ds**2):
                cst = (1+ds)*(j+1)
                cst2 = (ds**2 + i) + (j * ds**2)
                arr[cst2,f] = arr[cst2,f] + cst
    """
    elements = []
    skip = (ds + 1) ** 2
    dn = ds + 1
    idx = 0
    for k in range(ds):
        for j in range(ds):
            for i in range(ds):
                node = k * (dn) ** 2 + j * (dn) + i + 1
                idx += 1
                elements.append(
                    [
                        idx,
                        skip + node + dn,
                        skip + node,
                        node,
                        node + dn,
                        skip + node + dn + 1,
                        skip + node + 1,
                        node + 1,
                        node + dn + 1,
                    ]
                )

    arr = np.array(elements)

    arr = np.array(arr.astype("int"), dtype="str")
    for i in range(8):
        arr[:, i] = np.char.add(arr[:, i], ",")

    head = "*Element, type=C3D8, elset=ALLEL "
    np.savetxt(
        fname=os.path.join(save_dir, element_file),
        X=arr,
        fmt="%s",
        header=head,
        comments="",
    )

    # ------------- Node Set File -------------#
    x0 = ds + 1
    x1 = (ds + 1) ** 2
    x2 = (ds + 1) ** 3 - (ds + 1) ** 2 + 1
    x3 = (ds + 1) ** 3
    # these are indexing elements (or nodes?) so they must be shifted to the right in python
    k1 = np.arange(1, x1 + 1)
    k2 = np.arange(x2, x3 + 1)

    main_vec = np.zeros((6, x1))

    # setting XY face
    main_vec[0, :] = k1
    main_vec[1, :] = k2

    # setting XZ face
    xz1 = np.arange(1, x0 + 1)
    xz2 = np.arange((x0**2 - ds), x1 + 1)
    vxz1 = []
    vxz2 = []
    for j in range(x0):
        setxz1 = xz1 + ((x0**2) * j)
        setxz2 = xz2 + ((x0**2) * j)
        vxz1 = np.append(vxz1, setxz1)
        vxz2 = np.append(vxz2, setxz2)

    main_vec[2, :] = vxz1
    main_vec[3, :] = vxz2

    # setting YZ face
    yz1 = np.arange(1, x1 - ds + 1, x0)
    yz2 = np.arange(x0, x1 + 1, x0)
    vyz1 = []
    vyz2 = []
    for j in range(x0):
        setyz1 = yz1 + ((x0**2) * j)
        setyz2 = yz2 + ((x0**2) * j)
        vyz1 = np.append(vyz1, setyz1)
        vyz2 = np.append(vyz2, setyz2)

    main_vec[4, :] = vyz1
    main_vec[5, :] = vyz2

    main_vec = main_vec.reshape(6, ds + 1, ds + 1)
    arr = np.array(main_vec.astype("int"), dtype="str")
    for i in range(6):
        arr[i, :] = np.char.add(arr[i, :], ",")

    # arr = arr.reshape(6, ds+1, ds+1)
    # the indeces are: z1, z2, y1, y2, x1, x2
    idx = ["z1", "z2", "y1", "y2", "x1", "x2"]
    header = "*Nset, nset = "
    comment = "**"

    with open(os.path.join(save_dir, nodeset_file), "w") as f:
        for i in range(6):
            f.write(header + idx[i])
            f.write("\n")
            for j in range(ds + 1):
                vals = str(arr[i][j])
                for char in "[]' ":
                    vals = vals.replace(char, "")
                f.write(vals)
            f.write("\n")
            f.write(comment)
            f.write("\n")

    # ------------- Boundary Condition Node Set File -------------#
    arr = np.swapaxes(arr, 1, 2)
    z1 = 0
    z2 = 1
    y1 = 2
    y2 = 3
    x1 = 4
    x2 = 5
    # m=1 p=2

    sxp = arr[x2, 1:ds, 1:ds]
    sxm = arr[x1, 1:ds, 1:ds]
    szp = arr[z2, 1:ds, 1:ds]
    szm = arr[z1, 1:ds, 1:ds]
    syp = arr[y2, 1:ds, 1:ds]
    sym = arr[y1, 1:ds, 1:ds]
    xpyp = arr[x2, ds, 1:ds]
    xpym = arr[x2, 0, 1:ds]
    xmyp = arr[x1, ds, 1:ds]
    xmym = arr[x1, 0, 1:ds]
    zpyp = arr[z2, 1:ds, ds]
    zpym = arr[z2, 1:ds, 0]
    zmyp = arr[z1, 1:ds, ds]
    zmym = arr[z1, 1:ds, 0]
    zpxp = arr[z2, ds, 1:ds]
    zpxm = arr[z2, 0, 1:ds]
    zmxp = arr[z1, ds, 1:ds]
    zmxm = arr[z1, 0, 1:ds]
    c1 = 1
    c2 = ds + 1
    c3 = (ds + 1) ** 2
    c4 = ds * (ds + 1) + 1
    c5 = ds * (ds + 1) ** 2 + 1
    c6 = ds * (ds + 1) ** 2 + ds + 1
    c7 = (ds + 1) ** 3
    c8 = ds * (ds + 1) + 1 + ds * (ds + 1) ** 2
    node_sets = [
        sxp,
        sxm,
        szp,
        szm,
        syp,
        sym,
        xpyp,
        xpym,
        xmyp,
        xmym,
        zpyp,
        zpym,
        zmyp,
        zmym,
        zpxp,
        zpxm,
        zmxp,
        zmxm,
        c1,
        c2,
        c3,
        c4,
        c5,
        c6,
        c7,
        c8,
    ]

    idx = [
        "Set-x+\n",
        "Set-x-\n",
        "Set-y+\n",
        "Set-y-\n",
        "Set-z+\n",
        "Set-z-\n",
        "x+y+\n",
        "x+y-\n",
        "x-y+\n",
        "x-y-\n",
        "y+z+\n",
        "y+z-\n",
        "y-z+\n",
        "y-z-\n",
        "z+x+\n",
        "z+x-\n",
        "z-x+\n",
        "z-x-\n",
        "c1\n",
        "c2\n",
        "c3\n",
        "c4\n",
        "c5\n",
        "c6\n",
        "c7\n",
        "c8\n",
    ]
    header = "*Nset, nset = "

    with open(os.path.join(save_dir, bc_nset_file), "w") as f:
        for i in range(len(idx)):
            vals = str(node_sets[i])
            for char in "[]' ":
                vals = vals.replace(char, "")
            f.write(header + idx[i])
            f.write(vals)
            f.write("\n")

    # ------------- Step File -------------#

    # set of all possible boundary strains to apply

    # xx, yy, zz, xy, xz, yz
    disps = [0, 0, 0, 0, 0, 0]

    disps[bc_component] = ds * applied_strain

    with open(os.path.join(save_dir, step_file), "w") as f:
        f.write("** ----------------------------------------------------------------\n")
        f.write("** \n")
        f.write("** STEP: Step-1\n")
        f.write("** \n")
        f.write("*Step, name=Step-1\n")
        f.write("*Static\n")
        f.write("0.02, 1., 1e-05, 0.5\n")
        f.write("** \n")
        f.write("** BOUNDARY CONDITIONS\n")
        f.write("** \n")
        f.write("** Name: c1 Type: Displacement/Rotation\n")
        f.write("*Boundary\n")
        f.write("**c1 is origin and should never be changed\n")
        f.write("c1,1,3,0\n")  # lock the origin in place
        f.write("*Boundary\n")
        f.write("** c2 is in the x direction from c1\n")
        f.write("** c4 is in the y direction from c1\n")
        f.write("** c5 is in the z direction from c1\n")
        f.write(f"c2,1,1,{disps[0]}\n")  # (x-x) tension
        f.write(f"c5,1,1,{disps[4]}\n")  # (x-z) shear
        f.write("*Boundary\n")
        f.write(f"c2,2,2,{disps[3]}\n")  # (x-y) shear
        f.write(f"c4,2,2,{disps[1]}\n")  # (y-y)  tension
        f.write("*Boundary\n")
        f.write(f"c5,3,3,{disps[2]}\n")  # (z-z) tension
        f.write(f"c4,3,3,{disps[5]}\n")  # (y-z) shear
        f.write("*Boundary\n")
        f.write("c2,3,3,0\n")  # lock (x-z) along bottom
        f.write("*Boundary\n")
        f.write("c5,2,2,0\n")  # lock (y-z) along side
        f.write("*Boundary\n")
        f.write("c4,1,1,0\n")  # lock (x-y) along side
        f.write("** \n")
        f.write("** OUTPUT REQUESTS\n")
        f.write("**\n")
        f.write("*output, field, frequency=0\n")
        f.write("*ELEMENT OUTPUT, POSITION=CENTROIDAL, ELSET=ALLEL\n")
        f.write("S\n")
        f.write("E\n")
        f.write("*NODE OUTPUT\n")
        f.write("U\n")
        f.write("**\n")
        f.write("*output, history, frequency=0\n")
        f.write("** \n")
        f.write("*el print, summary=yes, totals=yes, position=centroidal\n")
        f.write("S\n")
        f.write("E\n")
        f.write("**\n")
        f.write("*End Step\n")
    # ------------- Main File -------------#

    with open(os.path.join(save_dir, main_file), "w") as f:
        f.write("*INCLUDE, INPUT=" + os.path.join(save_dir, node_file) + "\n")
        f.write("*INCLUDE, INPUT=" + os.path.join(save_dir, element_file) + "\n")
        f.write("*INCLUDE, INPUT=" + os.path.join(save_dir, nodeset_file) + "\n")
        f.write("*INCLUDE, INPUT=" + os.path.join(save_dir, bc_nset_file) + "\n")
        f.write("*INCLUDE, INPUT=" + os.path.join(save_dir, pbc_file) + "\n")
        f.write("*INCLUDE, INPUT=" + os.path.join(save_dir, step_file) + "\n")


if __name__ == "__main__":
    args = parser.parse_args()
    # print(args.ds)

    # get CLI args and pass them into generator
    ds = int(args.ds)
    applied_strain = float(args.e)
    bc_component = int(args.bc_component)

    # now make and write out the mesh
    generate_abaqus_mesh(ds, applied_strain, bc_component)
