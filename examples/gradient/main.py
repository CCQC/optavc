
options_kwargs = {
  'template_file_path': "template.dat",
  'energy_regex'      : r"@DF-RHF Final Energy:\s+(-\d+\.\d+)",
  'success_regex'     : r"\*\*\* P[Ss][Ii]4 exiting successfully." ,
  'program'           : "psi4",
  'input_name'        : "input.dat",
  'output_name'       : "output.dat"
}

from optavc import options
options_obj = options.Options(**options_kwargs)

from optavc.template import TemplateFileProcessor
tfp = TemplateFileProcessor(open("template.dat").read(), options_obj)

from optavc.gradient import Gradient
import numpy as np
gradient_obj = Gradient(tfp.molecule, tfp.input_file_object, options_obj, path="GRAD")
gradient_obj.compute_gradient()
grad = gradient_obj.get_gradient()
enrg = gradient_obj.get_reference_energy()
print(grad)
print(np.array(grad))
print(enrg)

