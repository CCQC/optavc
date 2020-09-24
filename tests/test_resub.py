import pytest

from optavc.tests.utils import options_4_cluster
from optavc.findifcalcs import Gradient, Hessian
from optavc.options import Options
from optavc.template import TemplateFileProcessor

def create_findifcalc(calc_type, options):

    # Copied from main.py
    if options.get('xtpl') is not None:
        options.pop('xtpl')
    
    options_obj = Options(**options)

    # Make all required input_file objects required. xtpl job should only require 2

    if options_obj.xtpl:
        tfps = [TemplateFileProcessor(open(i).read(), options_obj) for i in
                options_obj.xtpl_templates]
        tfp = tfps[0]
        xtpl_inputs = [i.input_file_object for i in tfps]
    else:
        template_file_string = open(options_obj.template_file_path).read()
        tfp = TemplateFileProcessor(template_file_string, options_obj)
        xtpl_inputs = None

    input_obj = tfp.input_file_object
    molecule = tfp.molecule

    if xtpl_inputs:
        input_obj = xtpl_inputs

    if options_obj.xtpl:
        path = f'{calc_type}/high_corr'
    else:
        path = calc_type

    options_obj.path = path

    if calc_type == "HESSIAN":
        calc_obj = Hessian(molecule, input_obj, options_obj, path)
    elif calc_type == "GRADIENT":
        calc_obj = Gradient(molecule, input_obj, options_obj, path)
    else:
        assert False

    return calc_obj

options1, options2 = options_4_cluster()

@pytest.mark.parametrize("calc_type", ["HESSIAN", "GRADIENT"])
@pytest.mark.parametrize("options", [options1, options2])
def  test_collect_failures(calc_type, options):

    calc_obj = create_findifcalc(calc_type, options)

    calc_obj.collect_failures()
    print(calc_obj.failed) 
    assert calc_obj.failed[0].disp_num == 1
    assert len(calc_obj.failed) == 1

