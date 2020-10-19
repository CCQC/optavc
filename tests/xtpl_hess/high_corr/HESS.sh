#!/bin/sh
#$ -q gen4.q,gen6.q
#$ -N HESS
#$ -S /bin/sh
#$ -cwd
#$ -sync y
#$ -t 1-931
#$ -tc 931

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
echo "    Submitted using:   gen4.q,gen6.q molpro@2010.1.67+mpi 931"
echo "***********************************************************************"

# cd into individual task directory
cd $SGE_O_WORKDIR/$SGE_TASK_ID
vulcan load molpro@2010.1.67+mpi

export NSLOTS=4

molpro -n $NSLOTS --nouse-logfile --no-xml-output -o output.dat input.dat
