import shutil, os, re

import psi4

from optavc.options import Options
from . import optimize
from . import hessian
from .template import TemplateFileProcessor


def run_optavc_mpi():
    from optavc.mpi4py_iface import mpirun
    options_kwargs = {
        'template_file_path': "template.dat",
        'queue': "shared",
        'command': "qchem input.dat output.dat",
        'time_limit': "48:00:00",  # has no effect
        # 'memory'            : "10 GB", #calculator uses memory, number of nodes, and numcores to
        # distribute resources
        'energy_regex': r"CCSD\(T\) total energy[=\s]+(-\d+\.\d+)",
        'success_regex': r"beer",
        'fail_regex': r"coffee",
        'input_name': "input.dat",
        'output_name': "output.dat",
        # 'readhess'          : False,
        'mpi': True,  # set to true to use mpi, false to not
        # 'submitter'         : None,
        'maxiter': 20,
        'findif': {
            'points': 3
        },  # set to 5 if you want slightly better frequencies
        # 'job_array'         : True,
        'optking': {
            'max_force_g_convergence': 1e-7,  # tighter than this is not recommended
            'rms_force_g_convergence': 1e-7,
        }
    }

    options_obj = Options(**options_kwargs)
    mpirun(options_obj)


def run_optavc(jobtype, options_dict, restart_iteration=0, xtpl_restart=None, sow=True, path="."):
    """ optavc driver meant to unify input
    
    Parameters
    ----------
    jobtype: str
        generous with available strings for optimziation / hessian
    options_dict: dict
        should contain BOTH optavc and psi4 options
    restart_iteration: int
        corresponds to the iteration we should begin trying to sow gradients for
    xtpl_restart: str
        should be ['high_corr', 'large_basis', 'med_basis', 'small_basis']
    sow: bool
        if False optavc will try to reap only
    path: str
        for Hessian jobs only

    """

    options_obj = Options(**options_dict)

    psi4.core.clean() 

    if options_obj.xtpl:
        tfps = [TemplateFileProcessor(open(i).read(), options_obj) for i in
                options_obj.xtpl_templates]
        tfp = tfps[0]
        xtpl_inputs = [i.input_file_object for i in tfps]
    else:
        template_file_string = open(options_obj.template_file_path).read()
        tfp = TemplateFileProcessor(template_file_string, options_obj)
        xtpl_inputs = None

    input_obj = tfp.input_file_object
    molecule = tfp.molecule

    if jobtype.upper() in ['OPT', "OPTIMIZATION"]:
        opt_obj = optimize.Optimization(options_obj, input_obj, molecule, xtpl_inputs)
        opt_obj.run(restart_iteration, xtpl_restart)
    elif jobtype.upper() in ["HESS", "FREQUENCY", "FREQUENCIES", "HESSIAN"]:
        if options_obj.xtpl:
            hessian.xtpl_hessian(options_obj, molecule, xtpl_inputs, path, sow)
        else:
            hess_obj = hessian.Hessian(options_obj, input_obj, molecule, path=path)
            hess_obj.compute_hessian(sow)
    else:
        raise ValueError(
            "Can only run deriv or optimizations. For gradients see optimize.py to run or add wrapper here")
