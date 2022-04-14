# concatenate a set of h5 files into one giant np file

import glob
import h5py
import os
import numpy as np
from natsort import natsorted
import sys

output_dir = "c12_outputs"


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


basename = sys.argv[1]

concat_files(
    f"{output_dir}/{basename}", f"{basename}_responses.h5", ["stress", "strain"]
)

sdt = h5py.string_dtype(encoding="ascii")
concat_files(f"micros/{basename}", f"{basename}_micros.h5", ["micros"])
