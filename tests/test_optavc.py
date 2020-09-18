"""
This is not how a test suite should be created. This confirms our ability to make it through
optimization and hessian calculations with restarts and resubmissions also tested

For simplicity. Run pytest test_optavc.py

"""

import pytest
import os
import glob
import shutil
import re
import socket

import optavc

""" Functions for test setup """


def initialize():
    """Clear directory of all output """
    templates = ['template.dat', 'template1.dat', 'template2.dat', 'test_optavc.py']

    saved = []
    for name in templates:
        with open(name, 'r') as f:
            saved.append(f.read())

    # glob matches files in *nix matching expression returns list
    leftovers = [glob.glob(f'{os.getcwd()}/{string}') for string in ['STEP*', '*opt', 'psi.*',
                                                                     'output.default*', '.*']]
    del_list = [item for sublist in leftovers for item in sublist]  # flatten leftovers glob list

    for deletion in del_list:
        try:
            os.remove(deletion)
        except IsADirectoryError:
            shutil.rmtree(deletion, ignore_errors=True)

    for idx, backup in enumerate(saved):
        with open(templates[idx], 'w+') as f:
            f.write(backup)


def options_4_cluster():

    basic_options = {
        'template_file_path': "template.dat",
        'input_name': "input.dat",
        'output_name': "output.dat",
        'program': 'psi4',
        'energy_regex': r"\s+\*\s+CCSD\(T\)\stotal\senergy\s+=\s*(-\d*.\d*)",
        'maxiter': 100,
        'cluster': 'Vulcan',
        'name': 'optavc_test',
        'nslots': 4,
        'print': 3,
        'resub': True,
        'max_force_g_convergence': 1e-7,
        'ensure_bt_convergence': True,
        'hessian_write': True,
        'xtpl': False
    }

    xtpl_add_on = {
        'xtpl_templates': ["template1.dat", "template2.dat"],
        'xtpl_programs': ["psi4"],
        'xtpl_energy': [r"\s+CCSD\scorrelation\senergy\s+=\s*(-\d*.\d*)",
                        r"\s*MP2\/QZ\scorrelation\senergy\s*(-\d*.\d*)",
                        r"\s*MP2\/TZ\scorrelation\senergy\s*(-\d*.\d*)",
                        r"\s+MP2\scorrelation\senergy\s+=\s+(-\d*.\d*)",
                        r"\s*SCF\/QZ\s+reference\senergy\s*(-\d*.\d*)"],
        'xtpl_corrections': r"\s+\(T\)\s*energy\s+=\s+(-\d*.\d*)",
        'xtpl_success': [r"beer"],
        'xtpl_basis_sets': [4, 3],
        'xtpl_input_style': [2, 2],
        'xtpl': True
    }

    xtpl_options = basic_options.copy()
    xtpl_options.update(xtpl_add_on)

    if 'sapelo' in socket.gethostname():
        # Not all keywords will be used in each test
        sapelo_extras = {
            'cluster': 'Sapelo',
            'queue': 'batch',
            'memory': '10GB',
            'time_limit': '00:10:00'
        }

        basic_options.update(sapelo_extras)
        xtpl_options.update(sapelo_extras)
        xtpl_options.update(xtpl_add_on)

        return basic_options, xtpl_options
    elif 'ss-sub' in socket.gethostname():
        sap2test = {
            "cluster": 'Sap2test',
            "queue": "batch",
            "memory": "4GB",
            "time_limit": '00:10:00'
        }
        basic_options.update(sap2test)
        xtpl_options.update(sap2test)
        xtpl_options.update(xtpl_add_on)

        return basic_options, xtpl_options

    elif 'vlogin' in socket.gethostname():

        return basic_options, xtpl_options
    else:
        raise RuntimeError("Cannot run test suite on this computer")


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


options1, options2 = options_4_cluster()

""" Tests """


@pytest.mark.parametrize("options", [options1, options2])
def test_opt(options):
    """ Run a normal optimization for O2. Once the optimization is done delete some singlepoints
    at STEP02 try to restart the last step
    """

    initialize()
    xtpl = options.pop('xtpl')

    assert optavc.run_optavc("OPT", options, restart_iteration=0)

    remove_outputs(xtpl)

    # rerun optimization starting at iteration 6
    assert optavc.run_optavc("OPT", options, restart_iteration=4)

    options.update({'xtpl': xtpl})


@pytest.mark.parametrize("options", [options1, options2])
def test_hessian(options):
    """ Run a Hessian. Stop. Try to re-reap that Hessian stop. Delete some singlepoints and
    re-reap """

    initialize()
    xtpl = options.pop('xtpl')

    print('First Hessian calculation sow should be True\n')
    assert optavc.run_optavc("HESS", options, sow=True)

    print('Second Hessian calculation sow should be False\n')
    assert optavc.run_optavc("HESS", options, sow=False)

    remove_outputs(xtpl, hess=True)

    print('Third Hessian calculation sow should be False\n')
    assert optavc.run_optavc("HESS", options, sow=False)

    options.update({'xtpl': xtpl})
    assert False


test_hessian(options1)
