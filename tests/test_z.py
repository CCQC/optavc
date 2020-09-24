"""
This is named test_z.py solely so that it runs last. Abort if tests fail before this


This is not how a test suite should be created. This confirms our ability to make it through
optimization and hessian calculations with restarts and resubmissions also tested

For simplicity. Run pytest test_optavc.py

"""

import pytest
import os
import glob
import shutil
import re

import optavc
from optavc.tests.utils import options_4_cluster

""" Functions for test setup """


def initialize():
    """Clear directory of all output """
    templates = ['template.dat', 'template1.dat', 'template2.dat', 'test_z.py']

    saved = []
    for name in templates:
        with open(name, 'r') as f:
            saved.append(f.read())

    # glob matches files in *nix matching expression returns list
    leftovers = [glob.glob(f'{os.getcwd()}/{string}') for string in ["HESS", 'STEP*', '*opt', 'psi.*',
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

    try:
        assert optavc.run_optavc("OPT", options, restart_iteration=0)

        remove_outputs(xtpl)

        # rerun optimization starting at iteration 6
        assert optavc.run_optavc("OPT", options, restart_iteration=4)
    finally:
        options.update({'xtpl': xtpl})


@pytest.mark.parametrize("options", [options1, options2])
def test_hessian(options):
    """ Run a Hessian. Stop. Try to re-reap that Hessian stop. Delete some singlepoints and
    re-reap """

    initialize()
    xtpl = options.pop('xtpl')

    try:
        print('First Hessian calculation sow should be True\n')
        assert optavc.run_optavc("HESS", options, sow=True)

        print('Second Hessian calculation sow should be False\n')
        assert optavc.run_optavc("HESS", options, sow=False)

        remove_outputs(xtpl, hess=True)

        print('Third Hessian calculation sow should be False\n')
        assert optavc.run_optavc("HESS", options, sow=False)
    finally:
        options.update({'xtpl': xtpl})

