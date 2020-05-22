import optavc

options_kwargs = {
  'template_file_path': "template.dat",
  'energy_regex'      : r"@DF-RHF Final Energy:\s+(-\d+\.\d+)",
  'success_regex'     : r"\*\*\* P[Ss][Ii]4 exiting successfully." ,
  'queue'             : "gen3.q",
  'program'           : "psi4@master",
  'input_name'        : "input.dat",
  'output_name'       : "output.dat",
  'job_array'         : True,
  'findif'            : {"hessian_write": True, #ALWAYS have this on
                         "normal_modes_write": True}
}

optavc.run_optavc("HESS", options_kwargs, path="HESS", sow=False)

