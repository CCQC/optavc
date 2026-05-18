#!/bin/bash
#SBATCH --partition=batch
#SBATCH --constraint="EPYC|Intel"
#SBATCH --job-name=STEP
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=10:00:00
#SBATCH --mem=32GB
#SBATCH --output="%x.%j".out    # Standard output log
#SBATCH --error="%x.%j".err     # Standard error log

cd $SLURM_SUBMIT_DIR
export NSLOTS=4

export PSI_SCRATCH=/scratch/$USER/tmp/$SLURM_JOB_ID
mkdir -p $PSI_SCRATCH
psi4 -n $NSLOTS
rm $PSI_SCRATCH -r

# ignored line -- do not remove
