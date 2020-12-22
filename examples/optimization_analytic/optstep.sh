#!/bin/sh
#$ -q 
#$ -N STEP--00
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


vulcan load psi4@master

export NSLOTS=4

psi4 -n $NSLOTS