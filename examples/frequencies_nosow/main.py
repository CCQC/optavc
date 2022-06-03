import optavc
options_kwargs = {
  'template_file_path': "template.dat",
  'energy_regex'      : r"\@DF-RHF Final Energy\:\s+(-\d+\.\d+)",
  'program'           : "psi4",
  'input_name'        : "input.dat",
  'output_name'       : "output.dat"
}

optavc.run_optavc("FREQUENCIES", options_kwargs, sow=False)
