import pytest
import random
import copy

import optavc

# lists defined up here to avoid weird formatting
hess = [1, 3, 4, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 135, 136, 137, 138, 243, 456, 654, 769, 
        811, 812, 813, 814, 815, 832]
hess_xtpl = [[1, 2, 5, 8, 9, 10, 26, 27, 28, 29, 30, 31, 32, 33, 66, 67, 68, 172, 173, 174, 175, 
             176, 342, 345, 348, 351, 352, 891, 892, 893], [val for val in range(800, 931)]]
grad = [[1, 3, 4, 10, 11, 12, 13, 34, 42, 61], [3, 4, 5], [57], []]
grad_xtpl = [[[1, 10, 15, 26, 27], [53, 54, 56, 59]], [[], []], [[], [3, 4, 5, 8, 9, 10]],
             [[val for val in range(50, 61)], []]]

ccsd = r"\s+UCCSD\scorrelation\senergy\s+\s*(-\d*.\d*)"
mp2 = r"\s+RHF-RMP2\scorrelation\senergy\s+=\s+(-\d*.\d*)"
hf = r"\s+Reference\senergy\s+(-\d*.\d*)"

options1  = {'template_file_path': f"calc_3_template.dat",
            'program': 'psi4',
            'energy_regex': r"\s*!RHF-UCCSD\(T\)\senergy\s+(-\d+\.\d+)",
            'resub': True}

options2 = copy.deepcopy(options1)
options2.update({'xtpl_templates': [['calc_3_template1.dat', 'calc_3_template2.dat'], 
                                    ['calc_3_template1.dat', 'calc_3_template2.dat']],
                 'xtpl_regexes': [[ccsd, hf], [ccsd, hf]],
                 'xtpl_basis_sets': [[4, 3], [4, 3]],
                 'xtpl_names': [['high_corr', 'low_corr'], ['high_corr', 'low_corr']]})  
# names are old didnt want to change

@pytest.mark.parametrize("options, failures, path", [(options1, hess, 'hess'), 
                                                      (options2, hess_xtpl, 'xtpl_hess')])
@pytest.mark.no_calc
def test_hessian_failures(options, failures, path):
    # the actual molecule doesn't really matter as long as it has the right number
    # of displacements. Pretend that template1 and template2 are different (they're the same)


    # our test hessian is actually the same calc twice. We pretend here that the ccsd and hf are pulled out of the same
    # output file for the qz and tz calculations
   
    options_obj, input_obj, molecule = optavc.initialize_optavc(options) 
    calc_obj, calc_type = optavc.create_calc_objects('HESS', molecule, options_obj, input_obj, path)

    if calc_obj.options.xtpl:
        
        for i in range(2):
            true_failures = failures[i]
            hess_obj = calc_obj.calc_objects[i] 

    else:
        true_failures = failures
        hess_obj = calc_obj
    
    iterative_collect_failures(hess_obj, true_failures, 10)
   

def make_comparison(hess_obj, true_failures): 
    calc_size = len(hess_obj.calculations)

    for i in range(20):
        assert_failures_match(hess_obj, true_failures)
        random_insertions = [random.randint(1, calc_size) for itr in range(30)]
        hess_obj.failed = hess_obj.failed + random_insertions
        hess_obj.collect_failures()
        assert_failures_match(hess_obj, true_failures)

@pytest.mark.skip()
@pytest.mark.parametrize("options, failures", [(options1, grad), (options2, grad_xtpl)])
@pytest.mark.no_calc
def test_gradient_failures(options, failures):
   
    options.update({'xtpl_energy': [r"\s*CCSD\s*correlation\s*energy\s+(-?\d+\.\d+)",
                                    r"\s*MP2\/QZ\scorrelation\senergy\s*(-\d*.\d*)",
                                    r"\s*MP2\/TZ\scorrelation\senergy\s*(-\d*.\d*)",
                                    r"\s*MP2\scorrelation\senergy:\s+(-\d*.\d*)",
                                    r"\s*SCF\/QZ\s+reference\senergy\s*(-\d*.\d*)"],
                    'xtpl_corrections': r"\s*Triples\s*\(T\)\s*contribution\s+(-\d*.\d*)",
                    'energy_regex': r"\s*\!CCSD\(T\)\s*total\s*energy\s*(-\d*.\d*)"})    
        
    molecule, input_obj, options_obj = create_needed_objects(options)

    for step in range(4):

        if options_obj.xtpl:
            calc_objects = xtpl_wrapper("GRADIENT", molecule, input_obj, options_obj,
                                        path=f"xtpl_grad", iteration=step)

            for corr_idx, calc_obj in enumerate(calc_objects):
                # xtpl_wrapper returns CCSD/DZ, MP2DZ, MP2/QZ, MP2/TZ, SCF/QZ gradients

                true_failures = failures[step][0]
                if corr_idx > 1:
                    true_failures = failures[step][1]

                iterative_collect_failures(calc_obj, true_failures, 10)

        else:
            true_failures = failures[step]
            calc_obj = Gradient(molecule, input_obj, options_obj, path=f"grad/STEP{step:02d}")
            iterative_collect_failures(calc_obj, true_failures, 10)


def iterative_collect_failures(calc_obj, true_failures, num):

    calc_size = len(calc_obj.calculations)

    for i in range(num):
        assert_failures_match(calc_obj, true_failures)
        random_insertions = [random.randint(1, calc_size) for itr in range(30)]
        calc_obj.failed = calc_obj.failed + random_insertions
        calc_obj.collect_failures()
        assert_failures_match(calc_obj, true_failures)


def assert_failures_match(calc_obj, true_failures):
    """Two way assertion that failures contains no errors """

    calc_obj.collect_failures()
    
    optavc_f_0_idx = [singlepoint.disp_num for singlepoint in calc_obj.failed]

    for val in optavc_f_0_idx:
        assert val in true_failures
    
    for val in true_failures:
        assert val in optavc_f_0_idx 

