# concatenate a set of h5 files into one giant np file

import glob
import h5py
import os
import numpy as np
from natsort import natsorted
import sys
import argparse

output_dir = "c12_outputs"

parser = argparse.ArgumentParser(description="Solve linear elasticity via MKS")

group = parser.add_mutually_exclusive_group()
group.add_argument("--split_micros", help="Split a given microstructure file")


def split_micros_file(micros_fname, samples_per_file=200):
    """Split a set of microstructures, batched in groups of `samples_per_file`
    This makes it easier to run them through abaqus, etc."""

    base_file = h5py.File(micros_fname)
    micros_dset = base_file["micros"]

    # rip out extension
    fbase = f"{os.path.splitext(micros_fname)[0]}"

    # how many microstructures will we need
    num_samples = micros_dset.shape[0]
    # how many files will we split across
    num_files = np.ceil(num_samples / samples_per_file).astype(int)
    f_ind = 1

    # split into chunks and save each chunk
    for i in range(0, num_samples, samples_per_file):
        print(f"Saving micros {i} to {i+samples_per_file - 1} of {num_samples}")

        # print(mic_i.shape)
        fname = f"{fbase}_{f_ind}.h5"
        output_f = h5py.File(fname, "w")
        f_ind += 1

        # which instances to grab?
        f_slice = slice(i, i + samples_per_file)
        print(f_slice)

        # grab a slice for every dataset
        for dset_key in base_file.keys():
            curr_dset = base_file[dset_key]
            data_key_slice = curr_dset[f_slice]
            # copy in data slice and copy relevant header info
            output_f.create_dataset(
                dset_key,
                data=data_key_slice,
                compression=curr_dset.compression,
                compression_opts=curr_dset.compression_opts,
                dtype=curr_dset.dtype,
            )

        # now add attributes directly to the microstructures dataset
        micros_dset = output_f["micros"]
        for k in micros_dset.attrs.keys():
            micros_dset.attrs.create(k, data=micros_dset.attrs[k])

        print(f"Saving to {fname}")
        output_f.close()


def concat_files(basename, output_file, keys):
    allDats = glob.glob(basename + "*.h5")
    allDats = natsorted(allDats)

    print(allDats)
    print(basename + "*.h5")

    big_file = h5py.File(output_file, "w")

    old_size = None

    for file_i in allDats:
        print(file_i)
        data_i = h5py.File(file_i, "r")
        for key in keys:
            curr_dataset = data_i.get(key, None)
            if curr_dataset is not None:
                if big_file.get(key) is None:
                    chunk_size = (1,) + curr_dataset.shape[1:]
                    # make new dataset for this
                    big_file.create_dataset(
                        key,
                        shape=curr_dataset.shape,
                        dtype=curr_dataset.dtype,
                        compression="gzip",
                        compression_opts=6,
                        maxshape=(None,) + curr_dataset.shape[1:],
                        chunks=chunk_size,
                    )
                    print(key, big_file[key].chunks)
                    big_file[key][:] = curr_dataset[:]
                else:
                    offset = big_file[key].shape[0]
                    added_size = curr_dataset.shape[0]
                    big_file[key].resize(offset + added_size, axis=0)
                    big_file[key][offset:] = curr_dataset[:]
            print("new size:", big_file[key].shape)
        data_i.close()

    # the dataset was previously unlimited in size, so we should reset that now
    for key in keys:
        print(f"Reformatting {key}")
        data = big_file[key][:]  # load in all data (expensive!)
        chunks = big_file[key].chunks
        del big_file[key]
        big_file.create_dataset(
            key, data=data, compression="gzip", compression_opts=6, chunks=chunks
        )


def main():

    args = parser.parse_args()

    print(args)
    if args.split_micros:
        print(args.split_micros)
        micro_file = args.split_micros

        split_micros_file(micro_file, samples_per_file=200)

    # basename = sys.argv[1]

    # concat_files(
    #     f"{output_dir}/{basename}", f"{basename}_responses.h5", ["stress", "strain"]
    # )

    # sdt = h5py.string_dtype(encoding="ascii")
    # concat_files(f"micros/{basename}", f"{basename}_micros.h5", ["micros"])


if __name__ == "__main__":
    main()
