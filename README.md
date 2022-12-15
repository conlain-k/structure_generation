# flexible_structure_generation
Set of scripts for generating n-phase microstructures and meshes for Abaqus


Generating microstructures

```
python3 generate_micros.py --o test
```

Write input files

```
python3 write_inps.py --m micros/test --bc_c 3 --c 50
```

Run a single inp through abaqus and dump its results in hdf5 form:
```
bash run_abaqus.sh <inp_file>
```


Or run an ensemble through pylauncher
```
python3 launch_gen.py inputs/test_cr50_bc3
```

Or get a slurm allocation and then use pylauncher
```
sbatch run_abaqus_pylauncher.sh inputs/test_cr50_bc3
```

# Set of files


# TODOS
- Debug
- Add support for non-elastic sims
    - add support for writing non stress/strain-entities
- Add PyLauncher support/swap out dask
- Debug
- Documentation + readme
    - Docstring support?
- Active learning scripts + plugin w/ optim & GRF codes
- Phoenix support

