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

##
# Hessian findif resub test options
#

ccsd = r"\s+UCCSD\scorrelation\senergy\s+\s*(-\d*.\d*)"
mp2 = r"\s+RHF-RMP2\scorrelation\senergy\s+=\s+(-\d*.\d*)"
hf = r"\s+Reference\senergy\s+(-\d*.\d*)"

input0 = 'templates/calc_3_template.dat'
input1 = 'templates/calc_3_template1.dat'
input2 = 'templates/calc_3_template2.dat'

options1  = {'template_file_path': input0,
            'program': 'molpro',
            'energy_regex': r"\s*!RHF-UCCSD\(T\)\s*energy\s+(-\d+\.\d+)",
            'resub': True}

options2 = copy.deepcopy(options1)
options2.update({'xtpl_templates': [[input1, input2], [input1, input2]],
                 'xtpl_regexes': [[ccsd, hf], [ccsd, hf]],
                 'xtpl_basis_sets': [[4, 3], [4, 3]],
                 'xtpl_names': [['high_corr', 'low_corr'], ['high_corr', 'low_corr']]})  

# names are old didnt want to change

##
# Gradient findif resub test options
#

mp2qz = r"^\s*MP2\/QZ\scorrelation\senergy\s*(-\d*.\d*)"
mp2tz = r"^\s*MP2\/TZ\scorrelation\senergy\s*(-\d*.\d*)"
scfqz = r"^\s*SCF\/QZ\s+reference\senergy\s*(-\d*.\d*)"
ccsdt = r"^\s*\!CCSD\(T\)\s*total\s*energy\s*(-\d*.\d*)"
mp2 = r"^\s*MP2\stotal\senergy:\s+(-\d+.\d+)"
 
options3  = {'template_file_path': input0,
            'program': 'molpro',
            'energy_regex': r"^\s*!CCSD\(T\)\s*total\s*energy\s*(-\d*.\d*)",    
            'resub': True}

options4 = copy.deepcopy(options3)
options4.update({'xtpl_templates': [[input2, input2], [input2, input2]],
                 'xtpl_regexes': [[mp2qz, mp2tz], [scfqz]],
                 'xtpl_basis_sets': [[4, 3], [4, 3]],
                 'xtpl_names': [['low_corr', 'low_corr'], ['low_corr', 'low_corr']],
                 'delta_names': [['high_corr', 'high_corr']],
                 'delta_templates': [[input1, input1]],
                 'delta_regexes': [[ccsdt, mp2]]})  

@pytest.mark.parametrize("options, failures, path", [(options1, hess, 'hess'), 
                                                      (options2, hess_xtpl, 'xtpl_hess')])
@pytest.mark.no_calc
def test_hessian_failures(options, failures, path):
    """ the actual molecule doesn't really matter as long as it has the right number
    of displacements. Pretend that template1 and template2 are different (they're the same)
    our test hessian is actually the same calc twice. We pretend here that the ccsd and hf are pulled out of the same
    # output file for the qz and tz calculations """

    options_obj, input_obj, molecule = optavc.initialize_optavc(options) 
    calc_obj, calc_type = optavc.create_calc_objects('HESS', molecule, options_obj, input_obj, path=f'{path}')

    if calc_obj.options.xtpl:
        
        for i in range(2):
            true_failures = failures[i]
            hess_obj = calc_obj.calc_objects[i] 

    else:
        true_failures = failures
        hess_obj = calc_obj
    
    iterative_collect_failures(hess_obj, true_failures, 10)

@pytest.mark.parametrize("options, failures, path", [(options3, grad, "grad"), (options4, grad_xtpl, "xtpl_grad")])
@pytest.mark.no_calc
def test_gradient_failures(options, failures, path):
    """Either output file or the regex lines are removed from the failures. Each list of failures is a STEP """  

    options_obj, input_obj, molecule = optavc.initialize_optavc(options)

    for step in range(4):

        calc_obj, calc_type = optavc.create_calc_objects("OPT", molecule, options_obj, input_obj, path=f'{path}')
        grad_obj = calc_obj.create_opt_gradient(iteration=step)

        if options_obj.xtpl:
                
            for index, xtpl_obj in enumerate(grad_obj.calc_objects):
                print(index, xtpl_obj.options.name)
                print(xtpl_obj.path)
                if index < 4:
                    true_failures = failures[step][1]
                else:
                    true_failures = failures[step][0]
                
                iterative_collect_failures(xtpl_obj, true_failures, 10)

        else:
            true_failures = failures[step]
            iterative_collect_failures(grad_obj, true_failures, 10)


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

