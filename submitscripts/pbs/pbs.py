pbs_basic = """#PBS -S /bin/bash
#PBS -q {q}
#PBS -N {name}
#PBS -l nodes=1:ppn={nslots}:Intel
#PBS -l mem={memory}
#PBS -l walltime={time}

cd $PBS_O_WORKDIR/
echo "PBS_JOBID is $PBS_JOBID"

export NSLOTS={nslots}
{prog}
# ignored newline - do not remove
"""


pbs_email = """#PBS -S /bin/bash
#PBS -q {q}
#PBS -N {name}
#PBS -l nodes=1:ppn={nslots}:Intel
#PBS -l mem={memory}
#PBS -l walltime={time}
#PBS -M {email}
#PBS -m {email_opts}

cd $PBS_O_WORKDIR/
echo "PBS_JOBID is $PBS_JOBID"

export NSLOTS={nslots}
{prog}
# ignored newline - do not remove
"""

