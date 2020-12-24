# use sapelo2 home area (called scratch)
# no need to copy set psi_scratch variable
psi4 = """module load PSI4/1.3.2_conda
 
export PSI_SCRATCH=/scratch/$USER/$SLURM_JOB_ID
psi4 -n $NSLOTS
rm $PSI_SCRATCH
"""

# copy everything to lscratch
# run from lscratch
# tar and copy back

psi4_lscratch = """module load PSI4/1.3.2_conda

export PSI_SCRATCH=/scratch/$USER/$SLURM_JOB_ID

if [-e input.dat] ; then cp $SLURM_SUBMIT_DIR/input.dat $PSI_SCRATCH/input.dat
cd $PSI_SCRATCH

psi4 -n $NSLOTS

if [-e output.dat ] ; then cp $PSI_SCRATCH/output.dat $SLURM_SUBMIT_DIR/output.dat

rm $PSI_SCRATCH -r
"""

# mpi only
# set scratch dir to home area

molpro_mpi = """module load intel/2019b
export PATH=$PATH:/work/jttlab/molpro/2010/bin/

export scratch_dir=/scratch/$USER/$SLURM_JOB_ID

time molpro -n $NSLOTS --nouse-logfile --no-xml-output -o output.dat -d $scratch_dir input.dat

rm $scratch_dir
"""

# mpi only
# copy everything to lscratch to run and set scratch to lscratch

molpro_mpi_lscratch = """module load intel/2019b

export PATH=$PATH:/work/jttlab/molpro/2010/bin/

export scratch_dir= /lscratch/$USER/$SLRUM_JOB_ID

cp $SLURM_SUBMIT_DIR/input.dat /lscratch/$USER/$SLURM_JOB_ID
cd $scratch_dir
time molpro -n $NSLOTS --nouse-logfile --no-xml-output -o output.dat -d $scratch_dir input.dat

if [-e input.dat] ; then cp $scratch_dir/input.dat $SLURM_SUBMIT_DIR/input.dat
if [-e output.dat] ; then cp $scratch_dir/output.dat $SLURM_SUBMIT_DIR/output.dat

tar -cvzf molpro_tmp.tar.gz $scratch_dir/*

rm $scratch_dir -r
"""

# mixed mpi / omp
# set scratch to user home area

molpro_mpi_omp = """module load intel/2019b
export PATH=$PATH:/work/jttlab/molpro/2010/bin/
scratch_dir=/scratch/$USER/$SLURM_JOB_ID

time molpro -n $NSLOTS -n -t {threads} --nouse-logfile --no-xml-output -o output.dat -d $scratch_dir input.dat
"""

# mixed mpi / omp
# runs from lscratch tar and copy back to working dir

molpro_mpi_omp_lscratch = """module load intel/2019b

export PATH=$PATH:/work/jttlab/molpro/2010/bin/
scratch_dir= /lscratch/$USER/$SLRUM_JOB_ID

cp $SLURM_SUBMIT_DIR/input.dat /lscratch/$USER/$SLURM_JOB_ID
cd $scratch_dir
time molpro -n $NSLOTS -t {threads} --nouse-logfile --no-xml-output -o output.dat -d $scratch_dir input.dat

if [-e input.dat] ; then cp $scratch_dir/input.dat $SLURM_SUBMIT_DIR/input.dat
if [-e output.dat] ; then cp $scratch_dir/output.dat $SLURM_SUBMIT_DIR/output.dat

tar -cvzf molpro_tmp.tar.gz $scratch_dir/*

rm $scratch_dir -r
"""

cfour_serial = """module=cfour/2.1-iompi-2018a-serial
export OMP_NUM_THREADS=$NSLOTS

scratch_dir=/scratch/$USER/$SLURM_JOB_ID

{cfour_common}
"""

cfour_serial_lscratch = """module=cfour/2.1-iompi-2018a-serial
export OMP_NUM_THREADS=$NSLOTS

scratch_dir=/lscratch/$USER/$SLURM_JOB_ID

{cfour_common}
"""

cfour_mpi = """module=cfour/2.1-iompi-2018a-mpi

scratch_dir=/scratch/$USER/$SLURM_JOB_ID
echo -e "\t$NSLOTS" > ./ncpu   # CFour appears to just claim any and all cpus

{cfour_common}
"""

cfour_mpi_lscratch = """module=cfour/2.1-iompi-2018a-mpi

scratch_dir=/lscratch/$USER/$SLURM_JOB_ID
echo -e "\t$NSLOTS" > ./ncpu   # CFour appears to just claim any and all cpus

{cfour_common}
"""


orca = """scratch_dir=/scratch/$USER/$SLURM_JOB_ID

{orca_common}
"""

orca_lscratch = """scratch_dir=/lscratch/$USER/$SLURM_JOB_ID

{orca_common}
"""

orca_common = """#Set MPI Variables
export OMP_NUM_THREADS=1
prefix=/opt/vulcan/opt/vulcan/linux-x86_64/intel-16.0.1/orca-4.2.1-rxskih7qdrjqvog2ndxmpkrzueoz3yiy

# Set other variables
base=`basename input.dat .dat`

# Copy Job/Executable Data
cp $SGE_O_WORKDIR/input.dat $scratch_dir/input.dat
if [ -e $base.xyz ]; then cp $base.xyz $scratch_dir/guess.xyz ; fi
if [ -e $base.gbw ]; then cp $base.gbw $scratch_dir/guess.gbw ; fi
if [ -e $base.hess ]; then cp $base.hess $scratch_dir/guess.hess ; fi
if [ -e product.xyz ]; then cp product.xyz $scratch_dir/product.xyz ; fi
if [ -e ts_guess.xyz ]; then cp ts_guess.xyz $scratch_dir/ts_guess.xyz ; fi

echo " Running orca on `hostname`"
echo " Running calculation..."

cd $scratch_dir
$prefix/bin/orca input.dat >& $SGE_O_WORKDIR/output.dat || exit 1

echo " Saving data and cleaning up..."
# delete any temporary files that my be hanging around.
rm -f *.tmp*
find . -type f -size +50M -exec rm -f {} \;
tar --exclude='*tmp*' --transform "s,^,Job_Data_$JOB_ID/," -vzcf $SGE_O_WORKDIR/Job_Data_$JOB_ID.tar.gz *

echo " Job complete on `hostname`."

rm $scratch_dir -r
"""

cfour_common = """
prefix=/apps/eb/$module/
module load $module

# Copy job data
cp $SLURM_SUBMIT_DIR/ZMAT $scratch_dir
cp $prefix/basis/GENBAS $scratch_dir
cp $prefix/basis/ECPDATA $scratch_dir
if [ -e JAINDX ]; then cp JAINDX $scratch_dir ; fi
if [ -e JOBARC ]; then cp JOBARC $scratch_dir ; fi
if [ -e FCMINT ]; then cp FCMINT $scratch_dir ; fi
if [ -e GENBAS ]; then cp GENBAS $scratch_dir ; fi
if [ -e ECPDATA ]; then cp ECPDATA $scratch_dir ; fi
if [ -e OPTARC ]; then cp OPTARC $scratch_dir ; fi
if [ -e ISOTOPES ]; then cp ISOTOPES $scratch_dir ; fi
if [ -e ISOMASS ]; then cp ISOMASS $scratch_dir ; fi
if [ -e initden.dat ]; then cp initden.dat $scratch_dir ; fi
if [ -e OLDMOS ]; then cp OLDMOS $scratch_dir ; fi 

echo " Running cfour on `hostname`"
echo " Running calculation..."

cd $scratch_dir
xcfour >& $SLURM_SUBMIT_DIR/output.dat
xja2fja

echo " Saving data and cleaning up..."
if [ -e ZMATnew ]; then cp -f ZMATnew $SLURM_SUBMIT_DIR/ZMATnew ; fi

# Create a job data archive file
tar --transform "s,^,Job_Data_$JOB_ID/," -vcf $SLURM_SUBMIT_DIR/Job_Data_$JOB_ID.tar OPTARC FCMINT FCMFINAL ZMATnew JMOL.plot JOBARC JAINDX FJOBARC DIPDER HESSIAN MOLDEN NEWMOS den.dat
if [ -e zmat001 ]; then tar --transform "s,^,Job_Data_$JOB_ID/," -vrf $SLURM_SUBMIT_DIR/Job_Data_$JOB_ID.tar zmat* ; fi
gzip $SLURM_SUBMIT_DIR/Job_Data_$JOB_ID.tar

echo " Job complete on `hostname`."

rm $scratch_dir -r
"""

progdict = {
    "serial": {
        "lscratch": {
            "psi4": psi4_lscratch,
            "cfour": cfour_serial_lscratch,
            },
        "scratch": {
            "psi4": psi4,
            "cfour": cfour_serial,
            "molpro": molpro_mpi_omp
            }
        },
    "mpi": {
        "lscratch": {
            "orca": orca_lscratch,
            "molpro": molpro_mpi_lscratch,
            "cfour": cfour_mpi_lscratch
            },
        "scratch": {
            "orca": orca,
            "molpro": molpro_mpi,
            "cfour": cfour_mpi
            }
        },
    "mixed": {
        "lscratch": {
            "molpro": molpro_mpi_omp_lscratch
            },
        "scratch": {
            "molpro": molpro_mpi_omp
            }
        }
}

