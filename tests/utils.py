import socket


def options_4_cluster():

    basic_options = {
        'template_file_path': "template.dat",
        'input_name': "input.dat",
        'output_name': "output.dat",
        'program': 'psi4',
        'energy_regex': r"\s+\*\s+CCSD\(T\)\stotal\senergy\s+=\s*(-\d*.\d*)",
        'maxiter': 100,
        'cluster': 'Vulcan',
        'name': 'test',
        'nslots': 4,
        'print': 3,
        'resub': True,
        'max_force_g_convergence': 1e-7,
        'ensure_bt_convergence': True,
        'hessian_write': True,
        'xtpl': False,
        'sleepy_sleep_time': 10,
    }

    xtpl_add_on = {
        'xtpl_templates': ["template1.dat", "template2.dat"],
        'xtpl_programs': ["psi4"],
        'xtpl_energy': [r"\s+CCSD\scorrelation\senergy\s+=\s*(-\d*.\d*)",
                        r"\s*MP2\/QZ\scorrelation\senergy\s*(-\d*.\d*)",
                        r"\s*MP2\/TZ\scorrelation\senergy\s*(-\d*.\d*)",
                        r"\s+MP2\scorrelation\senergy\s+=\s+(-\d*.\d*)",
                        r"\s*SCF\/QZ\s+reference\senergy\s*(-\d*.\d*)"],
        'xtpl_corrections': r"\s+\(T\)\s*energy\s+=\s+(-\d*.\d*)",
        'xtpl_success': [r"beer"],
        'xtpl_basis_sets': [4, 3],
        'xtpl_input_style': [2, 2],
        'xtpl': True
    }

    if 'sapelo' in socket.gethostname():
        # Not all keywords will be used in each test
        extras = {
            'cluster': 'Sapelo',
            'queue': 'batch',
            'memory': '10GB',
            'time_limit': '00:10:00'
        }
    elif 'ss-sub' in socket.gethostname():
        extras = {
            "cluster": 'Sap2test',
            "queue": "batch",
            "memory": "4GB",
            "time_limit": '00:10:00'
        }
    elif 'vlogin' in socket.gethostname():
        extras = {'queue': 'gen3.q',
                  'job_array': False}
    else:
        raise RuntimeError("Cannot run test suite on this computer")

    basic_options.update(extras)
    xtpl_options = basic_options.copy()
    xtpl_options.update(xtpl_add_on)
    return basic_options, xtpl_options
