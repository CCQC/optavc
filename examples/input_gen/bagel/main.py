# 1. build a submit function
import subprocess as sp
def submit(optns):
    print('Got to submission')

# 2. build an options object
from optavc.options import Options
options_kwargs = {
    'template_file_path': "template.json",
    'energy_regex'      : r"\d+\w+-\d+.\d+\w+0.\d+\w+\d+.\d+\n\w*\n    * SCF iteration converged.\n",
    'success_regex'     : "",
    'program'           : "BAGEL",
    'input_name'        : "input.json",
    'output_name'       : "output.dat",
    'submitter'         : submit,
    'maxiter'           : 20,
    'findif'            : {'points': 3}
}
options_obj = Options(**options_kwargs)

from optavc.template import TemplateFileProcessor
tfp = TemplateFileProcessor(open('template.json').read(), options_obj)

from optavc.singlepoint import SinglePoint
singlepoint_obj = SinglePoint(tfp.molecule, tfp.input_file_object, options_obj, path="SP")
singlepoint_obj.write_input()
singlepoint_obj.run()
print('Ran succesfully')
