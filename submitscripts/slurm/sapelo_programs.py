#  use sapelo2 work area (called scratch)
# no need to copy set psi_scratch variable

fermi = """module load Julia/1.11.6-gfbf-2023b
module load intel/2023b

julia {input_name} 

"""

psi4 = """export PSI_SCRATCH=/scratch/$USER/tmp/$SLURM_JOB_ID
mkdir -p $PSI_SCRATCH
export PATH=$PATH:/work/hfslab/mrcc/2020
psi4 -n $NSLOTS
rm $PSI_SCRATCH -r
"""

# copy everything to lscratch
# run from lscratch
# tar and copy back

psi4_lscratch = """export PSI_SCRATCH=/lscratch/$USER/tmp/$SLURM_JOB_ID
mkdir -p $PSI_SCRATCH
export PATH=$PATH:/work/hfslab/mrcc/2020

psi4 {input_name} -n $NSLOTS --output {output_name}

rm $PSI_SCRATCH -r
"""

# mpi only
# set scratch dir to home area but run from submit_dir

molpro_scratch_prefix = """
# to change scratch dir to use local machine scratch
export SCRATCH_DIR=/scratch/$USER/tmp/$SLURM_JOB_ID
mkdir -p $SCRATCH_DIR
export APPTAINER_BIND="$SLURM_SUBMIT_DIR,$SCRATCH_DIR"  # This binds the directory into the container so that output can be written.
"""

molpro_lscratch_prefix = """
# to change scratch dir to use local machine scratch
export SCRATCH_DIR=/lscratch/$USER/tmp/$SLURM_JOB_ID
mkdir -p $SCRATCH_DIR
export APPTAINER_BIND="$SLURM_SUBMIT_DIR,$SCRATCH_DIR"  # This binds the directory into the container so that output can be written.
"""

molpro = """module load intel/2022a
export PATH=$PATH:/work/hfslab/mrcc/2020
mpirun -n $NSLOTS apptainer exec /work/hfslab/containers/molpro-2021-gapr.sif \
molpro.exe input.dat --output $SLURM_SUBMIT_DIR/output.dat --nouse-logfile --directory $SCRATCH_DIR

rm $SCRATCH_DIR -r

"""

molpro_24 = """
export PATH=$PATH:/work/hfslab/mrcc/2020
singularity run /work/hfslab/containers/molpro-2024-gapr.sif -n $NSLOTS input.dat \
--output output.dat --nouse-logfile --directory $SCRATCH_DIR
rm $SCRATCH_DIR -r

"""

# mpi only
# copy everything to lscratch to run and set scratch to lscratch

molpro_24_mpi = molpro_scratch_prefix + molpro_24
molpro_24_mpi_lscratch = molpro_lscratch_prefix + molpro_24
molpro_mpi = molpro_scratch_prefix + molpro
molpro_mpi_lscratch = molpro_lscratch_prefix + molpro

orca_common = """#Set MPI Variables
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
/apps/eb/ORCA/6.1.0-OpenMPI-4.1.8-GCC-13.3.0-avx2/bin/orca {input_name} >& $SLURM_SUBMIT_DIR/{output_name} || exit 1

echo " Saving data and cleaning up..."
# delete any temporary files that my be hanging around.
rm -f *.tmp*
find . -type f -size +50M -exec rm -f {{}} \;
tar --exclude='*tmp*' --transform "s,^,Job_Data_$SLURM_JOB_ID/," -vzcf $SLURM_SUBMIT_DIR/Job_Data_$SLURM_JOB_ID.tar.gz *

echo " Job complete on `hostname`."

rm $scratch_dir -r
"""

orca = """scratch_dir=/scratch/$USER/tmp/$SLURM_JOB_ID
mkdir -p $scratch_dir
""" + orca_common

orca_lscratch = """scratch_dir=/lscratch/$USER/tmp/$SLURM_JOB_ID
mkdir -p $scratch_dir
""" + orca_common

cfour_prefix = """
# make sure MRCC is around just in case
export PATH=$PATH:/work/hfslab/mrcc/2020/
prefix=/apps/eb/$module/
module load $module

# Copy job data
if [[ -e input.dat && ! -e ZMAT ]]; then
  cp input.dat $scratch_dir/ZMAT
else
  cp $SLURM_SUBMIT_DIR/ZMAT $scratch_dir
fi

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
"""

cfour_suffix = """
echo " Saving data and cleaning up..."
if [ -e ZMATnew ]; then cp -f ZMATnew $SLURM_SUBMIT_DIR/ZMATnew ; fi
if [ -e GRD ]; then cp -f GRD $SLURM_SUBMIT_DIR/GRD ; fi
if [ -e FCMFINAL ]; then cp -f FCMFINAL $SLURM_SUBMIT_DIR/FCMFINAL ; fi

# Create a job data archive file
tar --transform "s,^,Job_Data_$SLURM_JOB_ID/," -vcf $SLURM_SUBMIT_DIR/Job_Data_$SLURM_JOB_ID.tar OPTARC FCMINT FCMFINAL ZMATnew JMOL.plot JOBARC JAINDX FJOBARC DIPDER HESSIAN MOLDEN NEWMOS den.dat
if [ -e zmat001 ]; then tar --transform "s,^,Job_Data_$SLURM_JOB_ID/," -vrf $SLURM_SUBMIT_DIR/Job_Data_$SLURM_JOB_ID.tar zmat* ; fi
gzip $SLURM_SUBMIT_DIR/Job_Data_$SLURM_JOB_ID.tar

echo " Job complete on `hostname`."

rm $scratch_dir -r
"""

xcfour_module = cfour_prefix + """
xcfour >& $SLURM_SUBMIT_DIR/{output_name}
xja2fja
""" + cfour_suffix

xcfour_container = cfour_prefix + """
# Silence all the IEEE signaling messages
export NO_STOP_MESSAGE=yes
# request devices (inifiniband) use openib BTL interface for openmpi 4
export OMPI_MCA_btl_openib_allow_ib=true

apptainer exec /work/hfslab/containers/cfour-2.1-foss-ompi.sif xcfour >& $SLURM_SUBMIT_DIR/{output_name}
apptainer exec /work/hfslab/containers/cfour-2.1-foss-ompi.sif xja2fja
""" + cfour_suffix

cfour_serial = """module=cfour/2.1-intel-2023a-serial
export OMP_NUM_THREADS=$NSLOTS

scratch_dir=/scratch/$USER/tmp/$SLURM_JOB_ID
mkdir -p $scratch_dir

""" + xcfour_module

cfour_serial_lscratch = """module=cfour/2.1-intel-2023a-serial
export OMP_NUM_THREADS=$NSLOTS

scratch_dir=/lscratch/$USER/tmp/$SLURM_JOB_ID
mkdir -p $scratch_dir

""" + xcfour_module

cfour_mpi = """module=OpenMPI/4.1.1-GCC-11.2.0 # no cfour mpi by gacrc
scratch_dir=/scratch/$USER/tmp/$SLURM_JOB_ID
mkdir -p $scratch_dir

echo -e "\t$NSLOTS" > ./ncpu   # CFour appears to just claim any and all cpus
echo -e "\t$NSLOTS" > $scratch_dir/ncpu
""" + xcfour_container

cfour_mpi_lscratch = """module=OpenMPI/4.1.1-GCC-11.2.0 # no cfour mpi by gacrc
scratch_dir=/lscratch/$USER/tmp/$SLURM_JOB_ID
mkdir -p $scratch_dir

echo -e "\t$NSLOTS" > ./ncpu   # CFour appears to just claim any and all cpus
echo -e "\t$NSLOTS" > $scratch_dir/ncpu
""" + xcfour_container

progdict = {
    "serial": {
        "lscratch": {
            "psi4": psi4_lscratch,
            "cfour": cfour_serial_lscratch,
            "fermi": fermi
            },
        "scratch": {
            "psi4": psi4,
            "cfour": cfour_serial,
            "fermi": fermi
            }
        },
    "mpi": {
        "lscratch": {
            "orca": orca_lscratch,
            "molpro": molpro_mpi_lscratch,
            "molpro_24": molpro_24_mpi_lscratch,
            "cfour": cfour_mpi_lscratch
            },
        "scratch": {
            "orca": orca,
            "molpro": molpro_mpi,
            "molpro_24": molpro_24_mpi,
            "cfour": cfour_mpi
            }
        }
}

