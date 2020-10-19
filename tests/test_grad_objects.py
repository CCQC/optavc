import os
import pytest

from optavc.findifcalcs import Gradient
from optavc.optimize import Optimization

from optavc.tests import utils

@pytest.mark.no_calc
def test_gradient_creation():

    options_1, options_2 = utils.options_4_cluster("calc_1")
    molecule_1, input_obj_1, options_obj_1 = utils.create_needed_objects(options_1)
    molecule_2, input_obj_2, options_obj_2 = utils.create_needed_objects(options_2)

    opt_1 = Optimization(molecule_1, input_obj_1, options_obj_1)
    opt_2 = Optimization(molecule_2, None, options_obj_2, input_obj_2)

    for iteration in range(60):

        grad_obj = opt_1.create_opt_gradient(iteration)

        assert grad_obj.path == os.path.realpath(f'STEP{iteration:02d}')
        assert grad_obj.options.name == f'test--{iteration:02d}'

        for singlepoint in grad_obj.singlepoints:
            assert singlepoint.path == os.path.realpath(f'./STEP{iteration:02d}/'
                                                        f'{singlepoint.disp_num}')
            assert singlepoint.options.name == (f'test--{iteration:02d}-'
                                                f'{singlepoint.disp_num}')

        for index, grad_tuple in enumerate(opt_2.create_xtpl_gradients(iteration,
                                                                       restart_iteration=20,
                                                                       user_xtpl_restart=True)):
            xtpl_grad_obj, xtpl_restart = grad_tuple
            assert xtpl_grad_obj.options.name == f'test--{iteration:02d}'
            if index in [0, 1]:
                assert xtpl_grad_obj.path == os.path.realpath(f'STEP{iteration:02d}/high_corr')
                for singlepoint in xtpl_grad_obj.singlepoints:
                    assert singlepoint.path == os.path.realpath(f'STEP{iteration:02d}/high_corr/'
                                                                f'{singlepoint.disp_num}')
                    assert singlepoint.options.name == (f'test--{iteration:02d}-'
                                                        f'{singlepoint.disp_num}')
            else:
                assert xtpl_grad_obj.path == os.path.realpath(f'STEP{iteration:02d}/low_corr')
                for singlepoint in xtpl_grad_obj.singlepoints:
                    assert singlepoint.path == os.path.realpath(f'STEP{iteration:02d}/low_corr/'
                                                                f'{singlepoint.disp_num}')
                    assert singlepoint.options.name == (f'test--{iteration:02d}-'
                                                        f'{singlepoint.disp_num}')


def test_complex_molecule():

    basic_options = {
        'template_file_path': "mixed_basis.dat",
        'input_name': "input.dat",
        'output_name': "output.dat",
        'program': 'psi4',
        'energy_regex': r"\s*\*\s*CCSD\(T\)\stotal\senergy\s+=\s*(-\d*.\d*)",
        'maxiter': 100,
        'cluster': 'Vulcan',
        'name': 'test',
        'nslots': 4,
        'print': 3,
        'resub': True,
        'max_force_g_convergence': 1e-7,
        'ensure_bt_convergence': True,
        'hessian_write': True,
        'xtpl': False,
        'sleepy_sleep_time': 10
    }

    molecule, template, options_obj = utils.create_needed_objects(basic_options)
    grad_obj = Gradient(molecule, template, options_obj, path='.')
    assert len(grad_obj.singlepoints) == 247

