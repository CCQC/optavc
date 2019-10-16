#Script to generate SLURM inputs for optmpi
import os
from subprocess import call
import sys

keywords = {"--N":"nnode",
            "--n":"nproc",
            "--c":"ncore",
            "--program":"program",
            "--t":"time",
            "--q":"queue",
            "--h":"hold",
            "--m":"memory"}

settings = {"nnode":None,
            "nproc":None,
            "ncore":None,
            "program":None,
            "time":"48:00:00",
            "queue":"regular",
            "hold":False,
            "memory":None}

for arg in sys.argv[1:]:
    assert "=" in arg
    sarg = arg.split("=")
    print(sarg)
    if sarg[0] in keywords:
        settings[keywords[sarg[0]]] = sarg[1]
    
if settings["program"] is None:
    print("program not set -- can't continue :(")
    
summ = 0
for i in settings:
    if settings[i] is None:
        summ += 1
if summ > 0:
    print("Key information unset!")
    for i in settings:
        if settings[i] is None:
            print(i)
    settings["hold"] = True
    #exit()
#if (summ <= 2) and (summ > 0):
  #  return

#print(summ)
template = """#!/bin/bash
#SBATCH --constraint=haswell
#SBATCH -N {nnode}
#SBATCH --qos={queue}
#SBATCH --time={time}

module load {program}
export OMP_NUM_THREADS={ncore}
srun -n {nproc} -c {ncore} python -u main.py
wait
"""

with open("submit.sh","w") as f: f.write(template.format(**settings))
if not settings["hold"]:
    call("sbatch submit.sh",shell=True)