"""
This is named test_z.py solely so that it runs last. Abort if tests fail before this


This is not how a test suite should be created. This confirms our ability to make it through
optimization and hessian calculations with restarts and resubmissions also tested

For simplicity. Run pytest test_optavc.py

"""

import pytest
import os
import socket
import time
import shutil
import copy

import optavc
from optavc.tests import utils

""" Functions for test setup """

host = socket.gethostname()
if 'ss-sub' in host or 'sapelo' in host or 'vlogin' in host:
    pass
else:
    pass
    # raise RuntimeError("This test cannot be run on this machine")


def remove_outputs(xtpl, hess=False):

    for i in range(1, 4):
        if not xtpl and not hess:
            os.remove(f'STEP02/{i}/output.dat')
        elif not xtpl and hess:
            os.remove(f"HESS/{i}/output.dat")
        elif xtpl and not hess:
            os.remove(f'STEP02/high_corr/{i}/output.dat')
        else:
            os.remove(f'HESS/high_corr/{i}/output.dat')


options1, options2 = utils.options_4_cluster("calc_1")

""" Tests """


@pytest.mark.parametrize("options", [options1, options2])
def test_opt(options):
    """ Run a normal optimization for O2. Once the optimization is done delete some singlepoints
    at STEP02 try to restart the last step
    """

    utils.initialize()
    xtpl = options.pop('xtpl')

    try:
        assert optavc.run_optavc("OPT", options, restart_iteration=0)
        time.sleep(10)
        remove_outputs(xtpl)
        time.sleep(10)
        assert optavc.run_optavc("OPT", options, restart_iteration=4)
    finally:
        options.update({'xtpl': xtpl})


@pytest.mark.parametrize("options", [options1, options2])
def test_hessian(options):
    """ Run a Hessian. Stop. Try to re-reap that Hessian stop. Delete some singlepoints and
    re-reap """

    utils.initialize()
    xtpl = options.pop('xtpl')

    try:
        print('First Hessian calculation sow should be True\n')
        assert optavc.run_optavc("HESS", options, sow=True)
        
        time.sleep(10)
        print('Second Hessian calculation sow should be False\n')
        assert optavc.run_optavc("HESS", options, sow=False)

        time.sleep(10)
        remove_outputs(xtpl, hess=True)

        time.sleep(10)
        print('Third Hessian calculation sow should be False\n')
        assert optavc.run_optavc("HESS", options, sow=False)
    finally:
        options.update({'xtpl': xtpl})

number = r"(-?\d*\.\d*)"
orca_regex = r"\s*FINAL\sSINGLE\sPOINT\sENERGY\s*" + number
psi4_regex = r"\s*\*\sCCSD\(T\)\stotal\senergy\s*=\s*" + number
ecc_regex = r"\s*CCSD\(T\)\s*energy\s*" + number
molpro_regex = r"\s*!CCSD\(T\)\s*total\s*energy\s*" + number

program_options = [({"program": 'psi4', "energy_regex": psi4_regex, "itr": 1}, 'serial'),
                   ({"program": 'psi4', "parallel": 'serial', "energy_regex": psi4_regex, "itr": 2}, 'serial'),
                   ({"program": 'orca', "energy_regex": orca_regex, "itr": 1}, 'mpi'),
                   ({"program": 'orca', "parallel": 'mpi', "energy_regex": orca_regex, "itr": 2}, 'mpi'),
                   ({"program": 'cfour', "parallel": 'serial', "energy_regex": ecc_regex, "itr": 1}, 'serial'),
                   ({"program": 'cfour', "energy_regex": ecc_regex, "itr": 2}, 'serial'),
                   ({"program": 'cfour@2.~mpi', "energy_regex": ecc_regex, "itr": 3}, 'serial'),
                   ({"program": 'cfour@2.+mpi', "energy_regex": ecc_regex, "itr": 4}, 'mpi'),
                   ({"program": 'molpro', "memory": "3GB", "energy_regex": molpro_regex, "itr": 1}, 'mpi'),
                   ({"program": 'molpro', 
                     "parallel": 'mixed', 
                     "threads": 2,
                     "memory": '3GB', 
                     "energy_regex": molpro_regex,
                     "itr": 2}, 'mixed')]

@pytest.mark.parametrize("options, expected", program_options) 
@pytest.mark.parametrize("cluster", ['sge', 'slurm'])
@pytest.mark.parametrize("scratch", ['scratch', 'lscratch'])
def test_programs(options, expected, cluster, scratch):

    if cluster == 'sge' and scratch == 'lscratch':
        pytest.skip()
    if cluster == 'sge' and 'ss-sub' in socket.gethostname():
        pytest.skip()
    if cluster == 'slurm' and 'vlogin' in socket.gethostname():
        pytest.skip()

    # need templates
    # options dictionaries
    options = copy.deepcopy(options)
    progname = options.get('program').split('@')[0]
    progdir = progname + f"_{options.pop('itr')}"
    template = progname + "_template.dat"
    
    options.update({'template_file_path': template})
    options_obj = optavc.options.Options(**options)
    
    shutil.rmtree(os.path.abspath(progdir), ignore_errors=True)

    assert options_obj.parallel == expected

    template_file_string = open(options_obj.template_file_path).read()
    tfp = optavc.template.TemplateFileProcessor(template_file_string, options_obj)
    input_obj = tfp.input_file_object
    molecule = tfp.molecule

    calc = optavc.calculations.SinglePoint(molecule, input_obj, options_obj, path=progdir)

    if cluster == 'sge' and 'vlogin' in socket.gethostname() or cluster == 'slurm' and 'ss-sub' in socket.gethostname():
        calc.write_input()
        calc.run()
        
        for i in range(3):
            time.sleep(15)

            if not calc.check_status(options_obj.energy_regex):
                assert False
            else:
                assert True

