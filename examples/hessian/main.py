# 1. build a submit function
import subprocess as sp
def submit(optns):
  sp.call([optns.program, "-i", optns.input_name, "-o", optns.output_name])

# 2. build an options object
from optavc.options import Options
options_kwargs = {
  'template_file_path': "template.dat",
  'energy_regex'      : r"@DF-RHF Final Energy:\s+(-\d+\.\d+)",
  'success_regex'     : r"\*\*\* P[Ss][Ii]4 exiting successfully." ,
  'program'           : "psi4",
  'input_name'        : "input.dat",
  'output_name'       : "output.dat",
  'submitter'         : submit
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

