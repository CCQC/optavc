# 1. build a submit function
import subprocess as sp
def submit(optns):
    print('Got to submission')


# 2. build an options object
from optavc.options import Options
options_kwargs = {
  'template_file_path': "template.dat",
  'energy_regex'      : r"@DF-RHF Final Energy:\s+(-\d+\.\d+)",
  'success_regex'     : r"\*\*\* P[Ss][Ii]4 exiting successfully." ,
  'program'           : "psi4",
  'input_name'        : "input.dat",
  'output_name'       : "output.dat",
  'submitter'         : submit,
  'job_array'         : False
}
options_obj = Options(**options_kwargs)

from optavc.template import TemplateFileProcessor
tfp = TemplateFileProcessor(open("template.dat").read(), options_obj)

from optavc.singlepoint import SinglePoint
singlepoint_obj = SinglePoint(tfp.molecule, tfp.input_file_object, options_obj, path="SP")
singlepoint_obj.write_input()
singlepoint_obj.run()
print('Ran succesfully')
