#!/bin/bash

dir=$1

if [ -z "${dir}" ]; 
then 
    dir="."
fi


exts=("msg" "sim" "com" "prt" "odb" "sta" "dat" "lck")

# remove all files with these extensions in the given directory
for ext in ${exts[@]};
do
    # ls ${dir}/*.${ext} -f
    rm ${dir}/*.${ext} -f
done