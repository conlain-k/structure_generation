import numpy as np
import re
import os
import sys
import glob
import h5py
from natsort import natsorted

# start-of-line regex
regex_start = '\s+(?:[0-9]+)'
# regex to capture a value
regex_num = '\s+([0-9E\-\.]+)'

# capture 6 numbers after start
regex_str = "".join([regex_start] + [regex_num] * 6)


def find_last_step(lines):
    for ind, l in enumerate(lines):
        cspl = l.split(',')
        if cspl[0].strip() == 'STEP TIME COMPLETED        1.00':
            # make sure we're on the last time step
            return ind

def find_table_start(lines, marker):
    for ind, l in enumerate(lines):
        spl = l.split()
        if (len(spl) >= 2) and (spl[0] == "ELEMENT") and (spl[1] == 'FOOT-') and (spl[2] == marker):
            return ind

def rip_data(lines):
    regex = re.compile(regex_str)
    vals_arr = []

    # go over each line that we are given
    for ind, l in enumerate(lines):
        match = regex.match(l)
        if match is not None:
            # get all values matched
            vals = match.groups()

            # convert to floats
            vals_f = list(map(float, vals))
            vals_arr.append(vals_f)
    return vals_arr



def parsedat(dat_file):
    with open(dat_file, 'r') as f:
        lines = f.readlines()

    # first, strip to last output step
    last_step_begin = find_last_step(lines)

    # throw out everything else
    lines = lines[last_step_begin:]

    # beginning of stress and strain data, respectively
    S_b = find_table_start(lines, "S11")
    E_b = find_table_start(lines, "E11")

    # if stresses appear first
    if S_b < E_b:
        stresses = rip_data(lines[S_b:E_b])
        strains = rip_data(lines[E_b:])

    else:
        # if strains appear first
        strains = rip_data(lines[E_b:S_b])
        stresses = rip_data(lines[S_b:])

    stresses = np.array(stresses)
    strains = np.array(strains)

    print(f"File parsed! Stresses have shape {stresses.shape}, strains have shape {strains.shape}") 

    return stresses, strains

def parseAllDats(basename):
    allDats = glob.glob(basename + "*.dat")
    allDats = natsorted(allDats)
    print("Parsing {} files".format(len(allDats)))
    stresses = []
    strains = []
    num = len(allDats)
    pf = num // 10
    for i, dat in enumerate(allDats):
        print(dat)
        se, st = parsedat(dat)
        if num > 10 and i % pf == (pf - 1):
            print(i+1, dat)
        stresses.append(se)
        strains.append(st)

    stresses = np.array(stresses)
    strains = np.array(strains) 

    print(stresses.shape, strains.shape)
    output_f = h5py.File(f"responses/{os.path.basename(basename)}_resp.h5", 'w') 
    
    # write stresses and strains, compressed
    output_f.create_dataset('stress', data=stresses, compression='gzip', compression_opts=6)
    output_f.create_dataset('strain', data=strains, compression='gzip', compression_opts=6)
    
    output_f.close()
    

if __name__ == '__main__':
    parseAllDats(sys.argv[1])

