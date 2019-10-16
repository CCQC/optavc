# 1. build a submit function
import vulcan.queue as vq
from optavc.options import Options
from optavc.regex import Bagel_regex
from optavc.template import TemplateFileProcessor
from optavc.singlepoint import SinglePoint

def submit(optns):
  vq.submit(optns.queue, optns.program, input=optns.input_name, output=optns.output_name, sync=True)

# 2. build an options object
options_kwargs = {
    'template_file_path': "template.json",
    'energy_regex'      : Bagel_regex.mrci,
    'success_regex'     : "",
    'queue'             : "gen4.q",
    'program'           : "bagel@master",
    'input_name'        : "input.json",
    'output_name'       : "output.dat",
    'submitter'         : submit,
    'maxiter'           : 20,
}
options_obj = Options(**options_kwargs)

tfp = TemplateFileProcessor(open('template.json').read(), options_obj)
singlepoint_obj = SinglePoint(tfp.molecule, tfp.input_file_object, options_obj, path="SP")
singlepoint_obj.write_input()
singlepoint_obj.run()
print(singlepoint_obj.get_energy_from_output())
