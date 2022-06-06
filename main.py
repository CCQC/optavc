"""
Wrapper's for running optavc with a single method call.


run_optavc() currently supports:
    running finite differences of singlepoints to calculate Hessians
    Running optimizations by performing finite differences of gradients.

run_optavc_mpi()
    has never been used or tested all code is legacy for use on NERSC. Use WILL require work

"""

import psi4

from optavc.options import Options
from . import optimize
from . import findifcalcs
from . import xtpl
from .template import TemplateFileProcessor
from .calculations import AnalyticHessian


def run_optavc(jobtype, 
               options_dict, 
               restart_iteration=0, 
               xtpl_restart=None, 
               sow=True, 
               path=".",
               test_input=False, 
               molecule=None):
    """Optavc driver to unify and simplify input. This is the only internal method of optavc a user should need to 
    interact with. Creates any needed internal class objects based on the provided dictionary.

    Performs an Optimization or Hessian calculation

    Parameters
    ----------
    jobtype: str
        upper and lowercase variants of HESS, FREQUENCY, FREQUENCIES, HESSIAN, OPT, and OPTIMIZATION are allowed    
    options_dict: dict
        should contain BOTH optavc and psi4 options for optking and the finite difference proecedure.
        should not contain ANY options relevant for the calculations that optking will submit.
    restart_iteration: int
        For optimizations only. orresponds to the iteration we should begin trying to sow gradients for
    sow: bool
        For hessians only. if False optavc will reap the hessian.
    path: str
        for Hessians only. Specifies where to write displacement directories.
    test_input: bool
        Check all calculation in STEP00, HESS, or otherwise. This is a good way to test that the energy regex
        is working as expected. Raises an AssertionError if optavc considers any calculations to have failed.

    Returns
    -------
    result : list[int] or list[list[int]]
        the gradient after optimization the hessian after a hessian calculation
    energy : int
        final energy or energy of non displaced point
    molecule : molecule.Molecule
        final molecule.
    """

    options_obj, input_obj, molecule = initialize_optavc(options_dict, molecule)
    xtpl_inputs = None

    if test_input:
        try:
            test_singlepoints(jobtype, molecule, options_obj, input_obj, xtpl_inputs, path)
        except AssertionError as e:
            print("test_singlepoints has failed. Please check regexes after running pytest on "
                  "test_gradobjects.py")
            print(str(e))
            raise

    calc_obj, calc_type = create_calc_objects(jobtype, molecule, options_obj, input_obj, path)

    if calc_type == 'OPT':
        result, energy, molecule = calc_obj.run(restart_iteration, xtpl_restart)
        return result, energy, molecule

    elif calc_type == 'HESS':
        
        if sow:
            calc_obj.compute_result()
        else:
            calc_obj.get_result(force_resub=True)
        
        final_hess_printout(calc_obj)
        return calc_obj.result, calc_obj.energy, calc_obj.molecule


def initialize_optavc(options_dict, molecule=None):
    """Create the three basic objects required for running optavc. Options, InputFile, Molecule """

    options_obj = Options(**options_dict)

    if options_obj.xtpl:
        options_obj.template_file_path = options_obj._xtpl_templates[0][0]

    template_file_string = open(options_obj.template_file_path).read()
    tfp = TemplateFileProcessor(template_file_string, options_obj)

    input_obj = tfp.input_file_object
    if not molecule:
        molecule = tfp.molecule 

    return options_obj, input_obj, molecule


def create_calc_objects(jobtype, molecule, options_obj, input_obj, path='.'):
    """Creates the internal classes optavc uses to keep track of displacements and calculations. Unfifies possible jobtype"""  
 
    if jobtype.upper() in ['OPT', "OPTIMIZATION"]:
        calc_obj = optimize.Optimization(molecule, input_obj, options_obj, path=path)
        calc_type = 'OPT'

    elif jobtype.upper() in ["HESS", "FREQUENCY", "FREQUENCIES", "HESSIAN"]:
        calc_type = 'HESS'
        if path == '.':
            path = './HESS'

        use_procedure, calc_obj = xtpl.xtpl_delta_wrapper("HESSIAN", molecule, options_obj, path)
        if not use_procedure:
     
            if options_obj.dertype == 'HESSIAN':
                calc_obj = AnalyticHessian(molecule, input_obj, options_obj, path)
            else:
                calc_obj = findifcalcs.Hessian(molecule, input_obj, options_obj, path)
    else:
        raise ValueError(
            """Can only run hessians or optimizations. For gradients see findifcalcs.py to run or
            add wrapper here""")
     
    return calc_obj, calc_type


def final_hess_printout(hess_obj):
    """ Here because we don't want printouts for each hessian in the XtpleDelta procedure """

    psi4.core.print_out("\n\n\n============================================================\n")
    psi4.core.print_out("========================= OPTAVC ===========================\n")
    psi4.core.print_out("============================================================\n")
    
    psi4.core.print_out("\nThe final computed hessian is:\n\n")        
    psi4_mol_obj = hess_obj.molecule.cast_to_psi4_molecule_object()
    wfn = psi4.core.Wavefunction.build(psi4_mol_obj, 'def2-tzvp')
    wfn.set_hessian(psi4.core.Matrix.from_array(hess_obj.result))
    wfn.set_energy(hess_obj.energy)
    psi4.core.set_variable("CURRENT ENERGY", hess_obj.energy)
    psi4.driver.vibanal_wfn(wfn)
    psi4.driver._hessian_write(wfn)    


def test_singlepoints(jobtype, molecule, options_obj, input_obj, xtpl_inputs=None, path=""):
    """ Method to test that the singlepoints which will be created in the course
    `jobtype` and their regexes will work with the output generated by from the given templates.
    Can be called from run_optavc by specifying test_input=True """

    if jobtype.upper() in ['OPT', "OPTIMIZATION"]:
        opt_obj = optimize.Optimization(molecule, input_obj, options_obj, xtpl_inputs)

        if opt_obj.options.xtpl:
            for gradient, _ in opt_obj.create_xtpl_gradients(iteration=0, restart_iteration=0,
                                                             user_xtpl_restart=False):
                ref_singlepoint = gradient.calculations[0]
                assert ref_singlepoint.check_status(ref_singlepoint.options.energy_regex)
                assert ref_singlepoint.get_result()
        else:
            # single gradient reap only
            gradient = opt_obj.create_opt_gradient(iteration=0)
            ref_singlepoint = gradient.calculations[0]
            assert ref_singlepoint.check_status(ref_singlepoint.options.energy_regex)
            assert ref_singlepoint.get_result()

    elif jobtype.upper() in ["HESS", "FREQUENCY", "FREQUENCIES", "HESSIAN"]:
        if path == '.':
            path = './HESS'

        use_procedure, xtpl_hess_obj = xtpl.xtpl_delta_wrapper("HESSIAN", molecule, options_obj,
                                                               path, iteration=0)
        if use_procedure:
            for hess_obj in xtpl_hess_obj.calc_objects:
                ref_singlepoint = hess_obj.calculations[0]
                assert ref_singlepoint.check_status(ref_singlepoint.options.energy_regex)
                assert ref_singlepoint.get_result()
        else:
            hess_obj = findifcalcs.Hessian(molecule, input_obj, options_obj, path)
            ref_singlepoint = hess_obj.calculations[0]
            assert ref_singlepoint.check_status(ref_singlepoint.options.energy_regex)
            assert ref_singlepoint.get_result()


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
