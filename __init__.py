import psi4

psi4.core.set_output_file('output.dat', True)
from .main import run_optavc, initialize_optavc, create_calc_objects
from . import findifcalcs
