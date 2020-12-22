import psi4

psi4.core.set_output_file('output.dat', True)
from .main import run_optavc
from . import findifcalcs
