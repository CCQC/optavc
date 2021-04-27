sge_basic = """#!/bin/sh
#$ -q {q}
#$ -N {name}
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

cd $SGE_O_WORKDIR

export NSLOTS={nslots}
THREADS={threads}

{prog}

"""

sge_array = """#!/bin/sh
#$ -q {q}
#$ -N {name}
#$ -S /bin/sh
#$ -cwd
#$ -sync y
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

export NSLOTS={nslots}
THREADS={threads}

{prog}

"""

