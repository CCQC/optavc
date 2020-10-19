import pytest
import os

from optavc.optimize import Optimization
from optavc.tests import utils


@pytest.mark.parametrize("restart_at, iterations_started", [(10, 12), (9, 8), (18, 17), (7, 7)])
@pytest.mark.parametrize("xtpl, xtpl_restart, low_corr_exists", [(True, True, True),
                                                                 (True, True, False),
                                                                 (True, False, True),
                                                                 (True, False, False),
                                                                 (False, False, False)])
@pytest.mark.no_calc
def test_dir_backup(xtpl, xtpl_restart, low_corr_exists, restart_at, iterations_started):

    utils.initialize()

    for step in range(iterations_started + 1):
        os.mkdir(f'./STEP{step:02d}')
        if xtpl:
            os.mkdir(f'./STEP{step:02d}/high_corr')
            os.mkdir(f'./STEP{step:02d}/low_corr')

            if not low_corr_exists and step == iterations_started:
                os.rmdir(f'./STEP{step:02d}/low_corr')

    options1, options2 = utils.options_4_cluster("calc_1")

    if xtpl:
        molecule, input_obj, options_obj = utils.create_needed_objects(options2)
        opt_obj = Optimization(molecule, None, options_obj, input_obj)
    else:
        molecule, input_obj, options_obj = utils.create_needed_objects(options1)
        opt_obj = Optimization(molecule, input_obj, options_obj)

    opt_obj.copy_old_steps(restart_at, xtpl_restart)

    if restart_at > iterations_started:
        # always safe to (try and) start new iterations should not copy anything
        assert not os.path.exists('./1_opt')

    if restart_at == iterations_started:
        # In certain xtpl_cases we may not need to copy and what we copy depends
        if xtpl_restart and not low_corr_exists:
            # same as starting a new (never before tried calculation)
            assert not os.path.exists('./1_opt')
        elif xtpl_restart and low_corr_exists:
            # copy everything last step should be copied entirely. high_corr and low_corr
            assert os.path.exists('./1_opt')
            steps = [f'STEP{step:02d}' for step in range(restart_at + 1)]
            for step in steps:
                assert os.path.exists(f'./1_opt/{step}')
            assert os.path.exists(f'1_opt/STEP{restart_at:02d}/low_corr')
        else:
            # copy everything
            assert os.path.exists('./1_opt')
            steps = [f'STEP{step:02d}' for step in range(restart_at + 1)]
            for step in steps:
                assert os.path.exists(f'./1_opt/{step}')

    if restart_at < iterations_started:
        # copy everything up to and including restart_at
        assert os.path.exists('./1_opt')
        steps = [f'STEP{step:02d}' for step in range(restart_at + 1)]
        for step in steps:
            assert os.path.exists(f'./1_opt/{step}')
        assert not os.path.exists(f'./1_opt/{restart_at}')






