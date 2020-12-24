slurm_basic = """#!/bin/bash
#SBATCH --partition={q}
#SBATCH --constraint=EPYC,Intel
#SBATCH --job-name={name}
#SBATCH --ntasks=1
#SBATCH --cpus-per-task={nslots}
#SBATCH --time={time}
#SBATCH --mem={memory}
#SBATCH --output="${SLURM_JOB_ID}.out"    # Standard output log
#SBATCH --error="${SLURM_JOB_ID}.err"     # Standard error log

cd $SLURM_SUBMIT_DIR
export NSLOTS={nslots}

{prog}
# ignored line -- do not remove
"""

slurm_email = """#!/bin/bash
#SBATCH --partition={q}
#SBATCH --constraint=EPYC,Intel
#SBATCH --job-name={name}
#SBATCH --ntasks=1
#SBATCH --cpus-per-task={nslots}
#SBATCH --time={time}
#SBATCH --mem={memory}
#SBATCH --output="${SLURM_JOB_ID}.out"    # Standard output log
#SBATCH --error="${SLURM_JOB_ID}.err"     # Standard error log
#SBATCH --mail-user="${USER}@uga.edu"
#SBTACH --mail-type={email_opts}

cd $SLURM_SUBMIT_DIR
export NSLOTS={nslots}

{prog}
# ignored line -- do not remove
"""

slurm_mpi = """#!/bin/bash
#SBATCH --job-name={name}             # Job name
#SBATCH --partition={q}               # Partition (queue) name
#SBATCH --constraint=EPYC,Intel
#SBATCH --nodes=1                     # Number of nodes
#SBATCH --ntasks={nslots}             # Number of MPI ranks
#SBATCH --ntasks-per-node={nslots}    # How many tasks on each node
#SBATCH --cpus-per-task={threads}     # Number of cores per MPI rank 
#SBATCH --mem-per-cpu={memory}        # Memory per processor
#SBATCH --time={time}
#SBATCH --output="${SLURM_JOB_ID}.out"    # Standard output log
#SBATCH --error="${SLURM_JOB_ID}.err"     # Standard error log

cd $SLURM_SUBMIT_DIR
export NSLOTS={nslots}

{prog}
#ignored line -- do not remove
"""

slurm_mpi_email = """#!/bin/bash
#SBATCH --job-name={name}             # Job name
#SBATCH --partition={q}               # Partition (queue) name
#SBATCH --constraint=EPYC,Intel
#SBATCH --nodes=1                     # Number of nodes
#SBATCH --ntasks={nslots}             # Number of MPI ranks
#SBATCH --ntasks-per-node={nslots}    # How many tasks on each node
#SBATCH --cpus-per-task={threads}     # Number of cores per MPI rank 
#SBATCH --mem-per-cpu={memory}        # Memory per processor
#SBATCH --time={time}
#SBATCH --output="${SLURM_JOB_ID}.out"    # Standard output log
#SBATCH --error="${SLURM_JOB_ID}.err"     # Standard error log
#SBATCH --mail-user="${USER}@uga.edu"
#SBTACH --mail-type={email_opts}

cd $SLURM_SUBMIT_DIR
export NSLOTS={nslots}

{prog}
#ignored line -- do not remove
"""
