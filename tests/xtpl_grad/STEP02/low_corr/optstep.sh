#!/bin/sh
#$ -q gen4.q,gen6.q
#$ -N opt
#$ -S /bin/sh
#$ -sync y
#$ -cwd
#$ -t 1-61
#$ -tc 61

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
vulcan load psi4@master

export NSLOTS=4

psi4 -n $NSLOTS
