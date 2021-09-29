import os
import pytest

import optavc

@pytest.mark.no_calc
def test_standard_grad():

    options = {'template_file_path': f"calc_1_template.dat",
        'program': 'psi4',
        'energy_regex': r"\s*\*\s*CCSD\(T\)\stotal\senergy\s+=\s*(-\d*.\d*)",
        'name': 'test',
    }

    options_obj, input_obj, molecule = optavc.initialize_optavc(options)
    calc_obj, calc_type = optavc.create_calc_objects('OPT', molecule, options_obj, input_obj)

    for iteration in range(99): 
        grad_obj = calc_obj.create_opt_gradient(iteration)
        assert grad_obj.path == os.path.realpath(f'STEP{iteration:02d}')
        assert grad_obj.options.name == f'test--{iteration:02d}'

        for singlepoint in grad_obj.calculations:
            assert singlepoint.path == os.path.realpath(f'./STEP{iteration:02d}/'
                                                        f'{singlepoint.disp_num}')
            assert singlepoint.options.name == (f'test--{iteration:02d}-'
                                                f'{singlepoint.disp_num}')

@pytest.mark.no_calc
@pytest.mark.parametrize("option1,option2,option3,option4,expected", 
    [([['calc_1_template2.dat', 'calc_1_template2.dat'], ['calc_1_template2.dat', 'calc_1_template2.dat']],
      [['calc_1_template1.dat', 'calc_1_template1.dat']], None, None, 
      ['large_c'] * 4 + ['delta_0'] * 2),
     ([['calc_1_template1.dat', 'calc_1_template2.dat'], ['calc_1_template1.dat', 'calc_1_template2.dat']],
      [['calc_2_template1.dat', 'calc_2_template1.dat']], None, None, 
      ['large_c', 'small_c', 'large_c', 'small_c'] + ['delta_0'] * 2),
     ([['calc_1_template1.dat', 'calc_1_template2.dat'], ['calc_2_template1.dat', 'calc_2_template2.dat']],
      [['calc_3_template.dat', 'calc_3_template.dat']], None, None, 
      ['large_c', 'small_c', 'large_ref', 'small_ref'] + ['delta_0'] * 2),
     ([['calc_1_template2.dat', 'calc_1_template2.dat'], ['calc_1_template2.dat', 'calc_1_template2.dat']],
      [['calc_1_template1.dat', 'calc_1_template1.dat']], [['xtpl_calc', 'xtpl_calc'], ['xtpl_calc', 'xtpl_calc']],
      [['ccsdt', 'ccsdt']], ['xtpl_calc'] * 4 + ['ccsdt'] * 2),
     ([['calc_1_template1.dat', 'calc_1_template2.dat'], ['calc_1_template1.dat', 'calc_1_template2.dat']],
      [['calc_2_template1.dat', 'calc_2_template1.dat']], [['qz', 'tz'], ['qz', 'tz']], 
      [['ccsdt', 'ccsdt']], ['qz', 'tz', 'qz', 'tz', 'ccsdt', 'ccsdt']),
     ([['calc_1_template1.dat', 'calc_1_template2.dat'], ['calc_2_template1.dat', 'calc_2_template2.dat']],
      [['calc_3_template.dat', 'calc_3_template1.dat']], [['mp2qz', 'mp2tz'], ['scfqz', 'scftz']], [['ccsdt', 'mp2']], 
      ['mp2qz', 'mp2tz', 'scfqz', 'scftz', 'ccsdt', 'mp2'])])
def test_xtpl_grad(option1, option2, option3, option4, expected):

    # Don't pay attention to the template names they don't correspond to necessarily
    # sensible combinations of calcs - we're just tricking optavc into different numbers
    # of calculations as being unique
    
    mp2_qz = r"\s*MP2\/QZ\scorrelation\senergy\s*(-\d*.\d*)"
    mp2_tz = r"\s*MP2\/TZ\scorrelation\senergy\s*(-\d*.\d*)" 
    scf_qz = r"\s*SCF\/QZ\s+reference\senergy\s*(-\d*.\d*)"
    scf_tz = r"\s*SCF\/TZ\s+reference\senergy\s*(-\d*.\d*)"

    options = {'template_file_path': f"calc_1_template.dat",
        'program': 'psi4',
        'energy_regex': r"\s*\*\s*CCSD\(T\)\stotal\senergy\s+=\s*(-\d*.\d*)",
        'xtpl_templates': option1,
        'xtpl_programs': "psi4",
        'xtpl_regexes': [[mp2_qz, mp2_tz], [scf_qz, scf_tz]],
        'xtpl_basis_sets': [[4, 3], [4, 3]], 
        'xtpl_names': option3,
        'delta_templates': option2,
        'delta_programs': 'psi4',
        'delta_names': option4,
        'delta_regexes': [["doesn't actually matter", "also doesnt matter"]]

    }

    options_obj, input_obj, molecule = optavc.initialize_optavc(options)
    calc_obj, calc_type = optavc.create_calc_objects('OPT', molecule, options_obj, input_obj)

    for iteration in range(10):
        xtpl_obj = calc_obj.create_opt_gradient(iteration) 
 
        for index, xtpl_grad_obj in enumerate(xtpl_obj.calc_objects):
            assert xtpl_grad_obj.options.name == f'{expected[index]}--{iteration:02d}'
            assert xtpl_grad_obj.path == os.path.realpath(f'STEP{iteration:02d}/{expected[index]}')

            for singlepoint in xtpl_grad_obj.calculations:
                assert singlepoint.path == os.path.realpath(f'STEP{iteration:02d}/{expected[index]}/'
                                                            f'{singlepoint.disp_num}')
                assert singlepoint.options.name == (f'{expected[index]}--{iteration:02d}-'
                                                    f'{singlepoint.disp_num}')

@pytest.mark.no_calc
def test_complex_molecule():
    """This is to make sure that atom labels are properly read especially for assigning mixed basis sets """

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
        'sleepy_sleep_time': 10
    }

    options_obj, input_obj, molecule = optavc.initialize_optavc(basic_options)
    calc_obj, calc_type = optavc.create_calc_objects('OPT', molecule, options_obj, input_obj)
    grad_obj = calc_obj.create_opt_gradient(iteration=0)
    assert len(grad_obj.calculations) == 247

