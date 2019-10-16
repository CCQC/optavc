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

# 3. call frequencies
from optavc.frequencies import Frequencies
frequencies_obj = Frequencies(options_obj)
frequencies_obj.run(sow=False)
