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
  'submitter'         : submit,
  'maxiter'           : 20,
  'findif'            : {'points': 5}
}
options_obj = Options(**options_kwargs)

# 3. call optimizer
from optavc.optimize import Optimization
optimization_obj = Optimization(options_obj)
optimization_obj.run()
