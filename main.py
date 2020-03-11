import shutil, os
import re
from optavc.mpi4py_iface import mpirun
from optavc.options import Options

options_kwargs = {
    'template_file_path': "template.dat",
    'queue': "shared",
    'command': "qchem input.dat output.dat",
    'time_limit': "48:00:00",  #has no effect
    # 'memory'            : "10 GB", #calculator uses memory, number of nodes, and numcores to
    # distribute resources
    'energy_regex': r"CCSD\(T\) total energy[=\s]+(-\d+\.\d+)",
    'success_regex': r"beer",
    'fail_regex': r"coffee",
    'input_name': "input.dat",
    'output_name': "output.dat",
    # 'readhess'          : False,
    'mpi': True,  #set to true to use mpi, false to not
    #'submitter'         : None,
    'maxiter': 20,
    'findif': {
        'points': 3
    },  #set to 5 if you want slightly better frequencies
    #'job_array'         : True,
    'optking': {
        'max_force_g_convergence': 1e-7,  #tighter than this is not recommended
        'rms_force_g_convergence': 1e-7,
    }
}

options_obj = Options(**options_kwargs)
mpirun(options_obj)
