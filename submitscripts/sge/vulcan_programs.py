# strings to handle unique program behavior such as moving to tmp directory and
# to perform the actual running of the program
# Taken from submit scripts written by J. Turney

fermi = """module load intel/19.0.1
export PATH=$PATH:/home/vulcan/aroeira/julia

julia {input_name} --threads $NSLOTS

"""

molpro = """vulcan load molpro@2010.1.67+mpi
molpro -n $NSLOTS --nouse-logfile --no-xml-output -o {output_name} {input_name}"""

molpro_mixed = """vulcan load molpro@2010.1.67+mpi
molpro -n $NSLOTS -t $THREADS --nouse-logfile --no-xml-output -o {output_name} {input_name}"""

psi4 = """vulcan load psi4@master
psi4 -n $NSLOTS
"""

orca = """# Set Orca Variables
vulcan load orca@4.2.1

#Set MPI Variables
export OMP_NUM_THREADS=1
prefix=/opt/vulcan/opt/vulcan/linux-x86_64/intel-16.0.1/orca-4.2.1-rxskih7qdrjqvog2ndxmpkrzueoz3yiy

# Set other variables
base=`basename input.dat .dat`

# Copy Job/Executable Data
cp $SGE_O_WORKDIR/input.dat $TMPDIR/input.dat
if [ -e $base.xyz ]; then cp $base.xyz $TMPDIR/guess.xyz ; fi
if [ -e $base.gbw ]; then cp $base.gbw $TMPDIR/guess.gbw ; fi
if [ -e $base.hess ]; then cp $base.hess $TMPDIR/guess.hess ; fi
if [ -e product.xyz ]; then cp product.xyz $TMPDIR/product.xyz ; fi
if [ -e ts_guess.xyz ]; then cp ts_guess.xyz $TMPDIR/ts_guess.xyz ; fi

echo " Running orca on `hostname`"
echo " Running calculation..."

cd $TMPDIR
$prefix/bin/orca {input_name} >& $SGE_O_WORKDIR/{output_name} || exit 1

echo " Saving data and cleaning up..."
# delete any temporary files that my be hanging around.
rm -f *.tmp*
find . -type f -size +50M -exec rm -f {} \;
tar --exclude='*tmp*' --transform "s,^,Job_Data_$JOB_ID/," -vzcf $SGE_O_WORKDIR/Job_Data_$JOB_ID.tar.gz *

echo " Job complete on `hostname`."

"""

cfour = """
scratch=$TMPDIR/$USER/$JOB_ID

# Set variables
prefix=/opt/vulcan/opt/vulcan/linux-x86_64/intel-13.0.0/cfour-2.0-yhj426etc3g7hslvbmpgvdymp2w76rob

# Copy job data
if [[ -e input.dat && ! -e ZMAT ]]; then
    cp input.dat $scratch/ZMAT
else
    cp $SGE_O_WORKDIR/ZMAT $scratch/ZMAT
fi

cp $prefix/basis/GENBAS $scratch
cp $prefix/basis/ECPDATA $scratch
if [ -e JAINDX ]; then cp JAINDX $scratch ; fi
if [ -e JOBARC ]; then cp JOBARC $scratch ; fi
if [ -e FCMINT ]; then cp FCMINT $scratch ; fi
if [ -e GENBAS ]; then cp GENBAS $scratch ; fi
if [ -e ECPDATA ]; then cp ECPDATA $scratch ; fi
if [ -e OPTARC ]; then cp OPTARC $scratch ; fi
if [ -e ISOTOPES ]; then cp ISOTOPES $scratch ; fi
if [ -e ISOMASS ]; then cp ISOMASS $scratch ; fi
if [ -e initden.dat ]; then cp initden.dat $scratch ; fi
if [ -e OLDMOS ]; then cp OLDMOS $scratch ; fi 

echo " Running cfour on `hostname`"
echo " Running calculation..."

cd $scratch
xcfour >& $SGE_O_WORKDIR/{output_name}
xja2fja
/opt/scripts/cfour2avogadro $SGE_O_WORKDIR/output.dat

echo " Saving data and cleaning up..."
if [ -e ZMATnew ]; then cp -f ZMATnew $SGE_O_WORKDIR/ZMATnew ; fi
if [ -e GRD ]; then cp -f GRD $SGE_O_WORKDIR/GRD ; fi
if [ -e FCMFINAL ]; then cp -f FCMFINAL $SGE_O_WORKDIR/FCMFINAL ; fi

# Create a job data archive file
tar --transform "s,^,Job_Data_$JOB_ID/," -vcf $SGE_O_WORKDIR/Job_Data_$JOB_ID.tar OPTARC FCMINT FCMFINAL ZMATnew JMOL.plot JOBARC JAINDX FJOBARC DIPDER HESSIAN MOLDEN NEWMOS AVOGADROplot.log den.dat
if [ -e zmat001 ]; then tar --transform "s,^,Job_Data_$JOB_ID/," -vrf $SGE_O_WORKDIR/Job_Data_$JOB_ID.tar zmat* ; fi
gzip $SGE_O_WORKDIR/Job_Data_$JOB_ID.tar

echo " Job complete on `hostname`."

"""

# only difference for the cfour scripts are the loaded module.
cfour_serial = """# Load the requested Cfour module file
vulcan load cfour@2.0~mpi+vectorization
export OMP_NUM_THREADS=$NSLOTS

""" + cfour

cfour_mpi = """# Load the requested Cfour module file
vulcan load cfour@2.0+mpi
export OMP_NUM_THREADS=1

""" + cfour

progdict = {
    "serial": {
        "scratch": {
            "psi4": psi4,
            "cfour": cfour_serial,
            "fermi": fermi
        }
    },
    "mpi": {
        "scratch": {
            "cfour": cfour_mpi, 
            "molpro": molpro,
            "orca": orca
        }
    },
    "mixed": {
        "scratch": {"molpro": molpro_mixed}
    }
}
