import optavc

options_kwargs = { 
    'input_name'         : "input.dat",
    'output_name'        : "output.dat",
    'maxiter'            : 100,
    'job_array'          : True,
    'print'              : 3,
    'resub'              : True,
    'cluster'            : 'sap2test',
    'nslots'             : 5,
    'memory'             : '5GB',
    'queue'              : 'batch',
    'time_limit'         : '00:00:40',
    'max_force_g_convergence': 1e-7,
    'ensure_bt_convergence': True,
    'xtpl_templates'     : ["template1.dat", "template2.dat"],
    'xtpl_programs'      : ["psi4@master"],
    'xtpl_energy'        : [r"\s+\s+CCSD\scorrelation\senergy\s+=\s*(-\d*.\d*)",
                            r"\s*MP2\/QZ\scorrelation\senergy\s*(-\d*.\d*)",
                            r"\s*MP2\/TZ\scorrelation\senergy\s*(-\d*.\d*)",
                            r"\s+MP2\scorrelation\senergy\s+=\s+(-\d*.\d*)",
                            r"\s*SCF\/QZ\s+reference\senergy\s*(-\d*.\d*)"],
    'xtpl_corrections'   : r"\s*\(T\)\senergy\s*=\s*(-\d*.\d*)", 
    'xtpl_success'       : [r"beer"],
    'xtpl_basis_sets'    : [4, 3], 
    'xtpl_input_style'   : [2, 2]
}

optavc.run_optavc('opt', options_kwargs)

