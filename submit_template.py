template = """#!/bin/sh
#$ -q {q}
#$ -N opt
#$ -S /bin/sh
#$ -sync y
#$ -cwd
#$ -t {jarray}
#$ -tc {tc}

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

# cd into individual task directory
cd $SGE_O_WORKDIR/$SGE_TASK_ID
vulcan load {prog}

export NSLOTS={nslots}

{cline}
"""
progdict = {
        "molpro":"molpro -n $NSLOTS --nouse-logfile --no-xml-output -o output.dat input.dat",
        "psi4":"psi4 -n $NSLOTS"
}
