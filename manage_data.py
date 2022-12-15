# concatenate a set of h5 files into one giant np file

import glob
import h5py
import os
import numpy as np
from natsort import natsorted
from math import ceil
import sys
import argparse

output_dir = "c12_outputs"

parser = argparse.ArgumentParser(description="Solve linear elasticity via MKS")

group = parser.add_mutually_exclusive_group()
group.add_argument("--split_micros", help="Split a given microstructure file")
group.add_argument("--ttv_split", help="Split a dataset into train-test-validate sets. Takes four args: <micro_file>, <resp_file>, <train relative fraction>, <test relative fraction>. Deduces validation size from other two. Relative fractions must be between zero and 1, and sum to 1 at most.", nargs = 4)
group.add_argument("--concat_files_dir", help="Directory full of files to concatenate")
group.add_argument(
	"--collect_fields",
	help="Directory full of files to concatenate. Takes three args: <target_file> <strain_name>, <stress_name>",
	nargs=3,
)

def collect_fields(fname, strain_file, stress_file):
	# take two .npy files containing strain and stress, and repack them into one .h5 file containing both (and compressed appropriately)
	output_f = h5py.File(fname, "w")

	strain = np.load(strain_file)
	stress = np.load(stress_file)

	# one chunk for each instance
	chunk_size = (1,) + strain[0].shape
	print("chunk size is", chunk_size)
	print(strain.dtype, strain.shape)
	print(stress.dtype, stress.shape)

	# now make the actual datasets
	output_f.create_dataset(
		"strain",
		data=strain,
		dtype=strain.dtype,
		compression="gzip",
		compression_opts=4,
		shuffle=True,
		chunks=chunk_size,
	)
	output_f.create_dataset(
		"stress",
		data=stress,
		dtype=stress.dtype,
		compression="gzip",
		compression_opts=4,
		shuffle=True,
		chunks=chunk_size,
	)


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
				shuffle=curr_dset.shuffle,
				dtype=curr_dset.dtype,
			)

		# now add attributes directly to the microstructures dataset
		micros_dset = output_f["micros"]
		for k in micros_dset.attrs.keys():
			micros_dset.attrs.create(k, data=micros_dset.attrs[k])

		print(f"Saving to {fname}")
		output_f.close()


def concat_files(basename, output_file, entries_per_file=1):
	allDats = glob.glob(basename + "/*.h5")
	allDats = natsorted(allDats)

	print(f"{len(allDats)} files total!")
	print(basename + "*.h5")

	if len(allDats) == 0:
		print("Directory has zero valid data files! Exiting.")
		exit(1)

	# maximum number of entries in big file is
	max_num_ents = entries_per_file * len(allDats)
	print(f"Max number of entries in big file is {max_num_ents}")

	big_file = h5py.File(output_file, "w")

	pf = max(1, (len(allDats) // 50))

	start_inds = {}

	# loop over every file we have
	for ind, file_i in enumerate(allDats[:]):
		# print 20 times total
		if ind % pf == 0:
			print(file_i)
		data_i = h5py.File(file_i, "r")
		# loop over every key in the file
		for key in data_i.keys():
			curr_dataset = data_i.get(key, None)
			# if we have that data, write it to the big file
			if curr_dataset is not None:
	

				# does the big file already have that field created?
				if big_file.get(key) is None:
					# 1 instance is a chunk
					chunk_size = (1,) + curr_dataset.shape[1:]

					# how many instances are we expecting
					newshape = (max_num_ents,) + curr_dataset.shape[1:]
					# make new dataset for this
					# allow resizing for now
					big_file.create_dataset(
						key,
						shape=newshape,
						dtype=curr_dataset.dtype,
						compression="gzip",
						compression_opts=4,
						shuffle=True,
						chunks=chunk_size,
					)
					print(f"Making dataset {key}, chunk size is {big_file[key].chunks}")
					start_inds[key] = 0 # pointer to where to write for this key

				entries = curr_dataset.shape[0]
				print(start_inds[key], entries)
				# now write our entries to the big file
				big_file[key][start_inds[key]:start_inds[key] + entries] = curr_dataset[:]

				# now augment our counter
				start_inds[key] = start_inds[key] + entries
		# done writing file i
		data_i.close()

	# Check how close to max we got
	for key in big_file.keys():
		print(
			f"Checking dataset {key}, size is {big_file[key].shape}, chunks is {big_file[key].chunks}, total entries added is {start_inds[key]}"
		)

def ttv_split(micro_file, resp_file, train_frac, test_frac):
	def check_frac(f):
		assert f >= 0.
		assert f <= 1.

	def write_split(name, hfile, inds, stype):
		# get new file names
		name_new = f"{os.path.splitext(name)[0]}_{stype}.h5"
		print("Writing to", name_new)
	
		hfile_new = h5py.File(name_new, 'w')
		# for now assume that all keys have the same length
		for k in hfile.keys():
			# just copy in data from 
			hfile_new.create_dataset(k, data=hfile[k][inds], shuffle=True, compression = 'gzip', compression_opts = 4, chunks = hfile[k].chunks)

		# now also write the indices
		hfile_new.create_dataset("inds", data=inds , compression = 'gzip')


	# check train and test fractions
	check_frac(train_frac) 
	check_frac(test_frac) 

	# now compute validation fraction and check that as well
	valid_frac = 1. - train_frac - test_frac
	check_frac(train_frac) 

	mf = h5py.File(micro_file)
	rf = h5py.File(resp_file)

	m_len = mf['micros'].shape[0]
	r_len = rf['strain'].shape[0]
	
	assert m_len == r_len	

	N_train = ceil(m_len * train_frac)
	N_test = ceil(m_len * test_frac)
	N_valid = ceil(m_len * valid_frac)

	# get ordering of indices
	inds = np.random.permutation(m_len)

	# take first indices for training set
	train_inds = inds[0:N_train]

	# second chunk for testing set
	test_inds = inds[N_train:N_train + N_test]

	# last chunk for validation set if any remain
	valid_inds = inds[N_train+N_test : N_train + N_test + N_valid]

	# now sort for easier indexing
	train_inds = sorted(train_inds)
	test_inds = sorted(test_inds)
	valid_inds = sorted(valid_inds)

	print(len(train_inds), len(test_inds), len(valid_inds))

	# write out split microstructures
	write_split(micro_file, mf, train_inds, "train")	
	write_split(micro_file, mf, test_inds, "test")	
	write_split(micro_file, mf, valid_inds, "valid")	

	# close micro file to make sure buffer is flushed	
	mf.close()

	# now write responses as well
	write_split(resp_file, rf, train_inds, "train")	
	write_split(resp_file, rf, test_inds, "test")	
	write_split(resp_file, rf, valid_inds, "valid")	



def main():

	args = parser.parse_args()

	print(args)
	# either split a micro file
	if args.split_micros:
		print(args.split_micros)
		micro_file = args.split_micros

		split_micros_file(micro_file, samples_per_file=200)

	# or concatenate other structures
	elif args.concat_files_dir:
		print(args.concat_files_dir)
		concat_dir = args.concat_files_dir
		# remove any trailing slashes to make file naming work right
		concat_dir = concat_dir.rstrip("/")

		concat_files(concat_dir, f"{concat_dir}_responses.h5")
	elif args.collect_fields:
		target_file = args.collect_fields[0]
		strain_file = args.collect_fields[1]
		stress_file = args.collect_fields[2]
		collect_fields(target_file, strain_file, stress_file)
	elif args.ttv_split:
		micro_file = args.ttv_split[0]
		resp_file = args.ttv_split[1]
		train_frac = float(args.ttv_split[2])
		test_frac = float(args.ttv_split[3])

		ttv_split(micro_file, resp_file, train_frac, test_frac)

	else:
		raise NotImplementedError()

	# basename = sys.argv[1]

	# concat_files(
	#	 f"{output_dir}/{basename}", f"{basename}_responses.h5", ["stress", "strain"]
	# )

	# sdt = h5py.string_dtype(encoding="ascii")
	# concat_files(f"micros/{basename}", f"{basename}_micros.h5", ["micros"])


if __name__ == "__main__":
	main()
