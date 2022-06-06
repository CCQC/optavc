from optavc.options import Options
options_kwargs = {
  'template_file_path': "template.dat",
  'energy_regex'      : r"@DF-RHF Final Energy:\s+(-\d+\.\d+)",
  'program'           : "psi4",
  'input_name'        : "input.dat",
  'output_name'       : "output.dat",
  'name'              : "STEP--00",
  'job_array'         : False
}
options_obj = Options(**options_kwargs)

from optavc.template import TemplateFileProcessor
tfp = TemplateFileProcessor(open("template.dat").read(), options_obj)

from optavc.calculations import SinglePoint
singlepoint_obj = SinglePoint(tfp.molecule, tfp.input_file_object, options_obj, path="SP")
enrg = singlepoint_obj.compute_result()
print(enrg)
