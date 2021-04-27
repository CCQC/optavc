import socket
import glob
import shutil
import os

from optavc.options import Options
from optavc.template import TemplateFileProcessor


def options_4_cluster(calc_string):

    basic_options = {
        'template_file_path': f"{calc_string}_template.dat",
        'input_name': "input.dat",
        'output_name': "output.dat",
        'program': 'psi4',
        'energy_regex': r"\s*\*\s*CCSD\(T\)\stotal\senergy\s+=\s*(-\d*.\d*)",
        'maxiter': 100,
         # 'cluster': 'Vulcan',
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
        'xtpl_templates': [f"{calc_string}_template1.dat", f"{calc_string}_template2.dat"],
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
            'cluster': 'Sapelo_old',
            'queue': 'batch',
            'memory': '10GB',
            'time_limit': '00:10:00'
        }
    elif 'ss-sub' in socket.gethostname():
        extras = {
            "cluster": 'Sapelo',
            "queue": "batch",
            "memory": "4GB",
            "time_limit": '00:10:00'
        }
    else:
        # if 'vlogin' in socket.gethostname():
        extras = {'queue': 'gen3.q',
                  'job_array': False}

    basic_options.update(extras)
    xtpl_options = basic_options.copy()
    xtpl_options.update(xtpl_add_on)
    return basic_options, xtpl_options


def create_needed_objects(options):

    # Copied from main.py
    if options.get('xtpl') is not None:
        options.pop('xtpl')
    
    options_obj = Options(**options)

    # Make all required input_file objects required. xtpl job should only require 2

    if options_obj.xtpl:
        tfps = [TemplateFileProcessor(open(i).read(), options_obj) for i in
                options_obj.xtpl_templates]
        tfp = tfps[0]
        xtpl_inputs = [i.input_file_object for i in tfps]
    else:
        template_file_string = open(options_obj.template_file_path).read()
        tfp = TemplateFileProcessor(template_file_string, options_obj)
        xtpl_inputs = None

    input_obj = tfp.input_file_object
    molecule = tfp.molecule

    if xtpl_inputs:
        input_obj = xtpl_inputs

    return molecule, input_obj, options_obj


def initialize():
    """Clear directory of all output """
    templates = ['template.dat', 'template1.dat', 'template2.dat', 'test_z.py']

    saved = []
    for name in templates:
        with open(name, 'r') as f:
            saved.append(f.read())

    # glob matches files in *nix matching expression returns list
    leftovers = [glob.glob(f'{os.getcwd()}/{string}') for string in ["HESS", 'STEP*', '*opt',
                                                                     'psi.*', 'output.default*',
                                                                     '.*']]
    del_list = [item for sublist in leftovers for item in sublist]  # flatten leftovers glob list

    for deletion in del_list:
        try:
            os.remove(deletion)
        except IsADirectoryError:
            shutil.rmtree(deletion, ignore_errors=True)

    for idx, backup in enumerate(saved):
        with open(templates[idx], 'w+') as f:
            f.write(backup)
