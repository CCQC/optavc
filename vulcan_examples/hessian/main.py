# 1. build a submit function
import vulcan.queue as vq
def submit(optns):
  vq.submit(optns.queue, optns.program, input=optns.input_name, output=optns.output_name, sync=True, job_array=optns.job_array_range)

# 2. build an options object
from optavc.options import Options
options_kwargs = {
  'template_file_path': "template.dat",
  'energy_regex'      : r"@DF-RHF Final Energy:\s+(-\d+\.\d+)",
  'success_regex'     : r"\*\*\* P[Ss][Ii]4 exiting successfully." ,
  'queue'             : "gen4.q",
  'program'           : "psi4@master",
  'input_name'        : "input.dat",
  'output_name'       : "output.dat",
  'submitter'         : submit,
  'job_array'         : True
}
options_obj = Options(**options_kwargs)

from optavc.template import TemplateFileProcessor
tfp = TemplateFileProcessor(open("template.dat").read(), options_obj)

from optavc.hessian import Hessian
import numpy as np
hessian_obj = Hessian(tfp.molecule, tfp.input_file_object, options_obj, path="HESS")
hessian_obj.compute_hessian()
hess = hessian_obj.get_hessian()
enrg = hessian_obj.get_reference_energy()
print(hess)
print(np.array(hess))
print(enrg)

