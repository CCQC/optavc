#!/bin/bash

#module load python
source activate my_dask_env
export PYTHONPATH=global/homes/m/md38294/bin/optavc:$PYTHONPATH #to get optavc in path

python -u $(which dask-scheduler) --scheduler-file $SCRATCH/scheduler.json --port 22463 & sleep 30
srun --mem=50G --gres=craynetwork:0 -u -n 5 python  -u $(which dask-worker) --scheduler-file $SCRATCH/scheduler.json --nthreads 1 --nprocs 1 --memory-limit 5000000000 & sleep 40
#for i in {1..5}
#do
   # srun --mem=5G --gres=craynetwork:0 -u -n 1 dask-worker --scheduler-file $SCRATCH/scheduler.json --nthreads 1 --nprocs 1 --memory-limit 5000000000 &
#done
#sleep 30
