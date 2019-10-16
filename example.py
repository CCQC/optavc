#Find initial Hessian
import shutil, os
from optavc.submitter import submitoptavc
options_kwargs = {
 'template_file_path': "template.dat",
 'queue'             : "shared",
 'program'           : "molpro",
 'prep_cmd'          : "module load molpro",
 'command'           : "molpro -n 8 --nouse-logfile --no-xml-output -o {}/output.dat {}/input.dat",
 'time_limit'        : "08:00:00",
 'memory'            : "4GB",
# 'num_cores'         : 1,
 'energy_regex'      : r" ENERGY\(1\)\s+=\s+(-\d+\.\d+)",
 'dask'              : "/global/cscratch1/sd/md38294/scheduler.json",
 'success_regex'     : r" Variable memory released",
 'input_name'        : "input.dat",
 'output_name'       : "output.dat",
 'submitter'         : submitoptavc,
 'maxiter'           : 20,
 'findif'            : {'points': 3},
 'job_array'         : True,
 'optking'           : {'max_force_g_convergence': 1e-7,
                        'rms_force_g_convergence': 1e-7,
                       }
}
from optavc.options import Options
options_obj = Options(**options_kwargs)
from optavc.optimize import Optimization
optimization_obj = Optimization(options_obj)
optimization_obj.run()
