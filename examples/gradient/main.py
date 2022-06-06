
options_kwargs = {
  'template_file_path': "template.dat",
  'energy_regex'      : r"@DF-RHF Final Energy:\s+(-\d+\.\d+)",
  'program'           : "psi4",
  'wait_time'         : 120,
  'input_name'        : "input.dat",
  'output_name'       : "output.dat"
}

from optavc import options
options_obj = options.Options(**options_kwargs)

from optavc.template import TemplateFileProcessor
tfp = TemplateFileProcessor(open("template.dat").read(), options_obj)

from optavc.findifcalcs import Gradient
import numpy as np
grad_obj = Gradient(tfp.molecule, tfp.input_file_object, options_obj, path="GRAD")
grad_obj.compute_result()
grad = grad_obj.reap()
enrg = grad_obj.get_reference_energy()
print(grad)
print(np.array(grad))
print(enrg)

