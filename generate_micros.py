#!/usr/bin/env python3

from pyDOE import lhs
from pymks.datasets import make_microstructure
import numpy as np

import os
import argparse

import json
import h5py


parser = argparse.ArgumentParser(description="Solve linear elasticity via MKS")
parser.add_argument("--output_name", required=True, help="What file to write to")

seed = 1

num_lhs_params = 4  # how many design params do we have
num_samples = 50  # 1000

# how often to print an update
pf = max(num_samples // 10, 1)
ds = 31  # number of voxels in one edge of the micro: total voxel count is ds^3
lengthscale = ds  # how "large" is one edge of the microstructure

base_dir = "micros"

plot_samp = True


def lhs_to_micro(lhs_val):
    """Convert a single lhs sample to microstructure parameters
    lhs_val is a sampled vector between zero and 1, latin-hypercube style
    lengthscale is how "long" a single microstructure is (in whatever consistent unit system you are using)"""
    gx, gy, gz, vf = lhs_val

    # all of the lhs values range from zero to 1
    # goal is to be between 1 and lengthscale
    gx = np.int32(np.ceil(gx * lengthscale))
    gy = np.int32(np.ceil(gy * lengthscale))
    gz = np.int32(np.ceil(gz * lengthscale))
    vf = np.float32(vf)  # convert to 32-bit float for storage purposes
    # vf = round(vf, 4) # round volume fraction

    vf = (vf, 1 - vf)

    # use different seed each time
    global seed
    seed += 1

    if seed % pf == 0:
        print(f"Generating structure {seed} of {num_samples}")

    # IMPORTANT: pass the seed into the generator
    X = make_microstructure(
        n_samples=1,
        size=(ds, ds, ds),
        n_phases=2,
        grain_size=(gx, gy, gz),
        volume_fraction=vf,
        seed=seed,
    )

    # now that we have our microstructure, shape it into a tensor field
    X = X.reshape(-1, ds, ds, ds)

    # dictionary for metadata
    metadata = {"gx": gx, "gy": gy, "gz": gz, "vf": vf[0]}

    return (X, metadata)


def gen_micros(num_samples):
    """Generate a set of microstructures using latin-hypercube sampling"""
    print("generating lhs points")
    points = lhs(num_lhs_params, num_samples)

    # generate a (micro, metadata) tuple for each lhs sample
    print("generating microstructures")
    micro_metas = list(map(lhs_to_micro, points))

    print("Reformatting data")
    # split micros and metas into two lists
    micros, metas = zip(*micro_metas)

    # now convert to numpy array
    micros = np.asarray(micros).squeeze().astype("int")

    # collect metadata into dict of arrays
    metas_dict = {}

    for k in metas[0].keys():
        # rip out data for key k from each entry
        meta_k = [m[k] for m in metas]
        metas_dict[k] = np.asarray(meta_k)

    return micros, metas_dict


def pretty_print(key, value):
    if isinstance(value, (int, np.int32, np.int64)):
        return f"{key}:{value}"
    else:
        # if not int, truncate for printing
        return f"{key}:{value:.2f}"


def save_micros(micros, metadata, fname):
    f = h5py.File(fname, "w")
    dset = f.create_dataset(
        "micros",
        data=micros,
        compression="gzip",
        compression_opts=6,
        dtype=int,
        chunks=(1, ds, ds, ds),
    )

    print(metadata.keys(), type(metadata.keys()))
    # use a dataset for the generation params as well
    for k in metadata.keys():
        f.create_dataset(name=f"params_{k}", data=metadata[k])
    dset.attrs.create("ds", data=ds)
    dset.attrs.create("num_phases", data=2)
    dset.attrs.create("gen_params", data=list(metadata.keys()))

    print(f)
    print(f.keys())
    print(f["micros"].attrs.keys())
    print(f["micros"].attrs["gen_params"])
    print(dset.compression)
    print(dset.compression_opts)
    print(dset.chunks)


def main():
    np.random.seed(0)

    args = parser.parse_args()
    output_name = args.output_name

    print(f"Generating {num_samples} LHS points!")

    micros, metas = gen_micros(num_samples)

    print(micros.shape)
    print(micros.dtype)
    print(metas.keys())

    print("Saving microstructures")
    # ensure our target directory actually exists
    os.makedirs(base_dir, exist_ok=True)
    save_micros(micros, metas, fname=f"{base_dir}/{output_name}.h5")

    print("displaying sample of microstructures")

    if plot_samp:
        show_inds = np.arange(8)
        micros_show = micros[show_inds]
        # print(micros_show.shape)
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(2, 4, figsize=(12, 8))
        for i in range(8):
            axi = ax.ravel()[i]
            axi.imshow(micros_show[i, :, :, 0].T, origin="lower")
            # print(micros_show[i].shape)
            axi.set_xlabel("x")
            axi.set_ylabel("y")

            mm_ind = show_inds[i]

            # print(metas_show[i])

            metastr = ",".join(pretty_print(k, metas[k][mm_ind]) for k in metas.keys())
            axi.set_title(metastr)
        fig.suptitle("z=0 slice of sampled microstructures")
        plt.tight_layout()

        gx_vals = sorted(metas["gx"])
        gx_vals = sorted(metas["gx"])
        vf_vals = sorted(metas["vf"])

        # print(gx_vals)

        plt.figure()
        plt.hist(
            gx_vals, bins=np.linspace(0.5, ds + 0.5, ds + 1), density=True, ec="black"
        )
        plt.xlabel("gx")
        plt.ylabel("frequency")
        plt.title("Grain size distribution for pymks sampler")
        plt.tight_layout()

        plt.figure()
        plt.hist(vf_vals, bins=51, density=True, ec="black")
        plt.xlabel("vf")
        plt.ylabel("frequency")
        plt.title("Volume fraction distribution for pymks sampler")
        plt.tight_layout()
        plt.show()


if __name__ == "__main__":
    main()
