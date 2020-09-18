#!/bin/bash
#SBATCH --constraint=haswell
#SBATCH -N 8
NNODE=8 # <-- this is used by optmpi to 
#SBATCH --time=24:00:00

module load qchem

NPROC=19
NCORE=4
TASKPERNODE=8
srun -n {nproc} -c {ncore} --ntasks-per-node=python -u main.py