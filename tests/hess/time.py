import os
import timeit
import re

stmt = """with open("34/output.dat") as f:
    text_output = f.read()
"""

print("Time to open file")
print(timeit.timeit(stmt=stmt, number=100)/100)


setup2 = """with open("34/output.dat") as f:
    text_output = f.read()
regex = r"^\s+CCSD\scorrelation\senergy\s+=\s*(-\d*.\d*)"
import re
"""

stmt2 = """re.search(regex, text_output, re.MULTILINE)"""

print("Non compiled regex. File opened in setup")
print(timeit.timeit(stmt=stmt2, setup=setup2, number=100)/100)

setup3 = """with open("34/output.dat") as f:
    text_output = f.read()
regex = r"\s+CCSD\scorrelation\senergy\s+=\s*(-\d*.\d*)"
import re
"""

stmt3 = """re.search(regex, text_output)"""

print("Compiled regex. File optned  in setup")
print(timeit.timeit(stmt=stmt3, setup=setup3, number=100)/100)


setup4 = """from optavc.options import Options
from optavc.template import TemplateFileProcessor
from optavc.findifcalcs import Hessian

def create_needed_objects(options):

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

    return molecule, input_obj, options_obj

from optavc.tests.utils import options_4_cluster
options1, options2 = options_4_cluster("../calc_3")
molecule, input_obj, options_obj = create_needed_objects(options1)
"""

stmt4 = """Hess = Hessian(molecule, input_obj, options_obj, path='')"""

print(timeit.timeit(stmt=stmt4, setup=setup4, number=100)/100)
