vulcan_template = """#!/bin/sh
#$ -q {q}
#$ -N opt
#$ -S /bin/sh
#$ -cwd

. /etc/profile.d/modules.sh

# Disable production of core dump files
ulimit -c 0

echo ""
echo "***********************************************************************"
echo " Starting job:"
echo ""
echo "    Name:              "$JOB_NAME
echo "    ID:                "$JOB_ID
echo "    Hostname:          "$HOSTNAME
echo "    Working directory: "$SGE_O_WORKDIR
echo ""
echo "    Submitted using:   optavc "
echo "***********************************************************************"

vulcan load {prog}

export NSLOTS={nslots}

{cline}
"""

# sapelo_template = """#PBS -S /bin/bash
# #PBS -q {q}
# #PBS -N {name}
# #PBS -l nodes=1:ppn={nslots}:Intel
# #PBS -l mem={memory}
# #PBS -l walltime={time}
# #PBS -t {jarray}
# #PBS -M {email}
# #PBS -m {email_opts}

# cd $PBS_O_WORKDIR/$PBS_ARRAYID
# echo "PBS_JOBID is $PBS_JOBID"

# {mod_load}
# export NSLOTS={nslots}
# time {cline}

# """

progdict = {
        "molpro":"molpro -n $NSLOTS --nouse-logfile --no-xml-output -o output.dat input.dat",
        "psi4":"psi4 -n $NSLOTS"
}

sapelo_mod_load = {
	"molpro": "export PATH=$PATH:/work/jttlab/molpro/2010/bin/",
	"psi4": "module load psi4/1.3.2_conda"
}

