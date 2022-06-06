import optavc
options_kwargs = {
  'template_file_path': "template.dat",
  'energy_regex'      : r"@DF-RHF Final Energy:\s+(-\d+\.\d+)",
  'correction_regexes': [r"\n\s+Correlation Energy\s+=\s+(-\d+\.\d+)"],
  'program'           : "psi4",
  'input_name'        : "input.dat",
  'output_name'       : "output.dat",
  'maxiter'           : 20,
  'findif'            : {'points': 5}
}

optavc.run_optavc("OPT", options_kwargs, restart_iteration=0)
