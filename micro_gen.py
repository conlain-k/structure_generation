from pyDOE import lhs
from pymks.datasets import make_microstructure
import numpy as np

import os

import json
import h5py

seed = 1

num_lhs_params = 4  # how many design params do we have
num_samples = 1000

# how often to print an update
pf = max(num_samples // 10, 1)
ds = 31  # number of voxels in one edge of the micro: total voxel count is ds^3
lengthscale = ds  # how "large" is one edge of the microstructure

base_dir = "micros"

plot_samp = False


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

    # print(gx, gy, gz, vf)

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

    # now convert to numpy arraus
    micros = np.asarray(micros).squeeze().astype("int")
    metas = np.asarray(metas).squeeze().astype(object)

    return micros, metas


def save_micros(micros, metadata=None, fbase="paper_micro_full", samples_per_file=200):
    """Save a set of microstructures, batched in groups of `samples_per_file`
    This makes it easier to run them through abaqus, etc."""
    # how many microstructures will we need
    num_samples = micros.shape[0]
    # how many files will we split across
    num_files = np.ceil(num_samples / samples_per_file).astype(int)

    # ensure our target directory actually exists
    os.makedirs(base_dir, exist_ok=True)

    # split into chunks and save each chunk
    for i in range(0, num_samples, samples_per_file):
        print(f"Saving micros {i + 1} to {i+samples_per_file} of {num_samples}")
        mic_i = micros[i : i + samples_per_file]

        # print(mic_i.shape)
        fname = f"{base_dir}/{fbase}_{i + 1}.h5"
        output_f = h5py.File(fname, "w")

        dset = output_f.create_dataset(
            "micros", data=mic_i, compression="gzip", compression_opts=6, dtype=int
        )
        if metadata is not None:
            met_i = metadata[i : i + samples_per_file]
            for key in met_i[0].keys():
                # print(key)
                met_dat_i_k = np.asarray([m[key] for m in met_i])
                # print(met_dat_i_k, met_dat_i_k.dtype)
                dset.attrs.create(name="metadata", data=met_dat_i_k)

            # string dataype to hold our json-ified metadata
            sdt = h5py.string_dtype(encoding="ascii")
            # output_f.create_dataset('metadata', data=met_i, compression='gzip', compression_opts=6, dtype=sdt)

        print(f"Saving to {fname}")
        output_f.close


def pretty_print(key, value):
    if isinstance(value, (int, np.int32, np.int64)):
        return f"{key}:{value}"
    else:
        # if not int, truncate for printing
        return f"{key}:{value:.2f}"


def main():
    np.random.seed(0)

    print(f"Generating {num_samples} LHS points!")

    micros, metas = gen_micros(num_samples)

    print(micros.shape, metas.shape)
    print(micros.dtype, metas.dtype)

    print("Saving microstructures")
    save_micros(micros, metas, fbase="newdata")

    print("displaying sample of microstructures")

    if plot_samp:
        micros_show = micros[:8]
        metas_show = metas[:8]
        # print(micros_show.shape)
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(2, 4, figsize=(12, 8))
        for i in range(8):
            axi = ax.ravel()[i]
            axi.imshow(micros_show[i, :, :, 0].T, origin="lower")
            # print(micros_show[i].shape)
            axi.set_xlabel("x")
            axi.set_ylabel("y")

            # print(metas_show[i])

            metastr = ",".join([pretty_print(k, v) for k, v in metas_show[i].items()])
            axi.set_title(metastr)
        fig.suptitle("z=0 slice of sampled microstructures")
        plt.tight_layout()

        gx_vals = sorted(np.array([m["gx"] for m in metas]))
        gx_vals = sorted(np.array([m["gx"] for m in metas]))
        vf_vals = sorted(np.array([m["vf"] for m in metas]))

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
