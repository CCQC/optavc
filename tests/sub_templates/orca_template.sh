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

scratch_dir=/scratch/$USER/tmp/$SLURM_JOB_ID
mkdir -p $scratch_dir
#Set MPI Variables
module load ORCA/6.1.0-OpenMPI-4.1.8-GCC-13.3.0-avx2
export OMP_NUM_THREADS=1

# Set other variables
base=`basename input.dat .dat`

# Copy Job/Executable Data
cp $SLURM_SUBMIT_DIR/input.dat $scratch_dir/input.dat
if [ -e $base.xyz ]; then cp $base.xyz $scratch_dir/guess.xyz ; fi
if [ -e $base.gbw ]; then cp $base.gbw $scratch_dir/guess.gbw ; fi
if [ -e $base.hess ]; then cp $base.hess $scratch_dir/guess.hess ; fi
if [ -e product.xyz ]; then cp product.xyz $scratch_dir/product.xyz ; fi
if [ -e ts_guess.xyz ]; then cp ts_guess.xyz $scratch_dir/ts_guess.xyz ; fi

echo " Running orca on `hostname`"
echo " Running calculation..."

cd $scratch_dir
/apps/eb/ORCA/6.1.0-OpenMPI-4.1.8-GCC-13.3.0-avx2/bin/orca input.dat >& $SLURM_SUBMIT_DIR/output.dat || exit 1

echo " Saving data and cleaning up..."
# delete any temporary files that my be hanging around.
rm -f *.tmp*
find . -type f -size +50M -exec rm -f {} \;
tar --exclude='*tmp*' --transform "s,^,Job_Data_$SLURM_JOB_ID/," -vzcf $SLURM_SUBMIT_DIR/Job_Data_$SLURM_JOB_ID.tar.gz *

echo " Job complete on `hostname`."

rm $scratch_dir -r

#ignored line -- do not remove
