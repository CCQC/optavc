"""
This is named test_z.py solely so that it runs last. Abort if tests fail before this


This is not how a test suite should be created. This confirms our ability to make it through
optimization and hessian calculations with restarts and resubmissions also tested

For simplicity. Run pytest test_optavc.py

"""

import pytest
import os
import socket

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

    # utils.initialize()
    xtpl = options.pop('xtpl')

    try:
        assert optavc.run_optavc("OPT", options, restart_iteration=0, test_input=True)

        remove_outputs(xtpl)

        # rerun optimization starting at iteration 6
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

        print('Second Hessian calculation sow should be False\n')
        assert optavc.run_optavc("HESS", options, sow=False)

        remove_outputs(xtpl, hess=True)

        print('Third Hessian calculation sow should be False\n')
        assert optavc.run_optavc("HESS", options, sow=False)
    finally:
        options.update({'xtpl': xtpl})

