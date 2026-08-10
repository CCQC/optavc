#!/bin/bash
#SBATCH --job-name=STEP             # Job name
#SBATCH --partition=batch               # Partition (queue) name
#SBATCH --constraint=EPYC|Intel
#SBATCH --nodes=1                     # Number of nodes
#SBATCH --ntasks=4             # Number of MPI ranks
#SBATCH --ntasks-per-node=4    # How many tasks on each node
#SBATCH --cpus-per-task=1     # Number of cores per MPI rank 
#SBATCH --mem=32GB                # Total Memory
#SBATCH --time=10:00:00
#SBATCH --output="%x.%j".out     # Standard output log
#SBATCH --error="%x.%j".err      # Standard error log

cd $SLURM_SUBMIT_DIR
export NSLOTS=4
export THREADS=1


# to change scratch dir to use local machine scratch
export SCRATCH_DIR=/scratch/$USER/tmp/$SLURM_JOB_ID
mkdir -p $SCRATCH_DIR
export APPTAINER_BIND="$SLURM_SUBMIT_DIR,$SCRATCH_DIR"  # This binds the directory into the container so that output can be written.
module load intel/2022a
mpirun -n $NSLOTS apptainer exec /work/jttlab/containers/molpro-2021-gapr.sif molpro.exe input.dat --output $SLURM_SUBMIT_DIR/output.dat --nouse-logfile --directory $SCRATCH_DIR

rm $SCRATCH_DIR -r


#ignored line -- do not remove
