psi4 = """module load PSI4/1.3.2_conda
psi4 -n $NSLOTS
"""

molpro = """export PATH=$PATH:/work/jttlab/molpro/2010/bin/
molpro -n $NSLOTS --nouse-logfile --no-xml-output -o output.dat input.dat
"""

progdict = {
    "serial": {"psi4": psi4, "molpro": molpro},
    "mpi": {"psi4": psi4, "molpro": molpro}
}
