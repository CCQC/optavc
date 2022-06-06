import optavc

options_kwargs = {
  'template_file_path': "template.dat",
  'deriv_regex'      : r"\s*-Total\sGradient:\n\s*Atom\s*X\s*Y\s*Z\n(\s*-*)*\n",
  'energy_regex'      : r"\s*@DF-RHF Final Energy:\s+(-\d+\.\d+)",
  'program'           : "psi4",
  'input_name'        : "input.dat",
  'output_name'       : "output.dat",
  'maxiter'           : 20,
  'dertype'           : 'GRADIENT'
}

optavc.run_optavc("OPT", options_kwargs, restart_iteration=0)
