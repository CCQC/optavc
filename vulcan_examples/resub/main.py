import optavc

options_kwargs = {
  'template_file_path': "template.dat",
  'energy_regex'      : r"@DF-RHF Final Energy:\s+(-\d+\.\d+)",
  'success_regex'     : r"\*\*\* P[Ss][Ii]4 exiting successfully." ,
  'queue'             : "gen3.q",
  'program'           : "psi4@master",
  'input_name'        : "input.dat",
  'output_name'       : "output.dat",
  'maxiter'           : 20,
  'job_array'         : True,
  'resub'             : True,
  'resub_test'        : True,
  'cluster'           : 'Vulcan',
  # 'g_convergence'     : "gau_verytight",
  # 'findif'            : {'points': 5}
}

optavc.run_optavc("OPT", options_kwargs, restart_iteration=0)
