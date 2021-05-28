# use sapelo2 work area (called scratch)
# no need to copy set psi_scratch variable

fermi = """ module load Julia/1.6.1-linux-x86_64
module load intel/2019b

julia {input_name} 

"""

psi4 = """module load PSI4/1.3.2_conda
 
export PSI_SCRATCH=/scratch/$USER/tmp/$SLURM_JOB_ID
mkdir -p $PSI_SCRATCH
psi4 -n $NSLOTS
rm $PSI_SCRATCH -r
"""

# copy everything to lscratch
# run from lscratch
# tar and copy back

psi4_lscratch = """module load PSI4/1.3.2_conda

export PSI_SCRATCH=/scratch/$USER/tmp/$SLURM_JOB_ID
mkdir -p $PSI_SCRATCH

psi4 {input_name} -n $NSLOTS --output {output_name}

rm $PSI_SCRATCH -r
"""

# mpi only
# set scratch dir to home area but run from submit_dir

molpro_mpi = """module load intel/2019b
export PATH=$PATH:/work/jttlab/molpro/2010/bin/

scratch_dir=/scratch/$USER/tmp/$SLURM_JOB_ID
mkdir -p $scrath_dir

time molpro -n $NSLOTS --nouse-logfile --no-xml-output --output {output_name} --directory $scratch_dir {input_name}

tar -cvzf molpro_tmp.tar.gz $scratch_dir/*
rm $scratch_dir

"""

# mpi only
# copy everything to lscratch to run and set scratch to lscratch

molpro_mpi_lscratch = """module load intel/2019b
export PATH=$PATH:/work/jttlab/molpro/2010/bin/

scratch_dir=/lscratch/$USER/tmp/$SLRUM_JOB_ID
mkdir -p $scratch_dir

time molpro -n $NSLOTS --nouse-logfile --no-xml-output --output {output_name} --directory $scratch_dir {input_name}

tar -cvzf molpro_tmp.tar.gz $scratch_dir/*
rm $scratch_dir -r
"""

# mixed mpi / omp
# set scratch to user home area runs from submit_dir

molpro_mpi_omp = """module load intel/2019b
export PATH=$PATH:/work/jttlab/molpro/2010/bin/
scratch_dir=/scratch/$USER/tmp/$SLURM_JOB_ID
mkdir -p $scratch_dir 

time molpro -n $NSLOTS -n -t $THREADS --nouse-logfile --no-xml-output --output $SLURM_SUBMIT_DIR/{output_name} --directory $scratch_dir {input_name}

tar -cvzf molpro_tmp.tar.gz $scratch_dir/*
rm $scratch_dir -r
"""

# mixed mpi / omp
# runs from lscratch tar and copy back to working dir

molpro_mpi_omp_lscratch = """module load intel/2019b
export PATH=$PATH:/work/jttlab/molpro/2010/bin/

scratch_dir=/lscratch/$USER/tmp/$SLRUM_JOB_ID
mkdir -p $scratch_dir

time molpro -n $NSLOTS -t $THREADS --nouse-logfile --no-xml-output --output {output_name} --directory $scratch_dir {input_name}

tar -cvzf molpro_tmp.tar.gz $scratch_dir/*
rm $scratch_dir -r
"""

orca_common = """#Set MPI Variables
module load ORCA/4.2.1-gompi-2019b
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
orca {input_name} >& $SLURM_SUBMIT_DIR/{output_name} || exit 1

echo " Saving data and cleaning up..."
# delete any temporary files that my be hanging around.
rm -f *.tmp*
find . -type f -size +50M -exec rm -f {} \;
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

cfour_common = """
# make sure MRCC is around just in case
export PATH=$PATH:/work/jttlab/mrcc/2019/
prefix=/apps/eb/$module/
module load $module

# Copy job data
if [[-e input.dat && ! -e ZMAT ]]; then
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
xcfour >& $SLURM_SUBMIT_DIR/{output_name}
xja2fja

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

cfour_serial = """module=cfour/2.1-iompi-2018a-serial
export OMP_NUM_THREADS=$NSLOTS

scratch_dir=/scratch/$USER/tmp/$SLURM_JOB_ID
mkdir -p $scratch_dir

""" + cfour_common

cfour_serial_lscratch = """module=cfour/2.1-iompi-2018a-serial
export OMP_NUM_THREADS=$NSLOTS

scratch_dir=/lscratch/$USER/tmp/$SLURM_JOB_ID
mkdir -p $scratch_dir

""" + cfour_common

cfour_mpi = """module=cfour/2.1-iompi-2018a-mpi
scratch_dir=/scratch/$USER/tmp/$SLURM_JOB_ID
mkdir -p $scratch_dir

echo -e "\t$NSLOTS" > ./ncpu   # CFour appears to just claim any and all cpus
echo -e "\t$NSLOTS" > $scratch_dir/ncpu
""" + cfour_common

cfour_mpi_lscratch = """module=cfour/2.1-iompi-2018a-mpi
scratch_dir=/lscratch/$USER/tmp/$SLURM_JOB_ID
mkdir -p $scratch_dir

echo -e "\t$NSLOTS" > ./ncpu   # CFour appears to just claim any and all cpus
echo -e "\t$NSLOTS" > $scratch_dir/ncpu
""" + cfour_common

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

