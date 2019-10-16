import vulcan.queue as vq
from optavc.options import Options
from optavc.regex import BagelRegex
from optavc.optimize import Optimization


def submit(optns):
    vq.submit(optns.queue, optns.program, input=optns.input_name, output=optns.output_name, sync=True, job_array=optns.job_array_range)

options_kwargs = {
    'template_file_path': "template.json",
    'energy_regex'      : BagelRegex.hf,
    'success_regex'     : "",
    'queue'             : "gen4.q",
    'program'           : "bagel@master",
    'input_name'        : "input.json",
    'output_name'       : "output.dat",
    'submitter'         : submit,
    'maxiter'           : 20,
    'job_array'         : True,
    'findif'            : {'points': 3},
}
options_obj = Options(**options_kwargs)

optimization_obj = Optimization(options_obj)
optimization_obj.run()
