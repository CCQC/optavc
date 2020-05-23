import copy
from .gradient import Gradient
from .hessian import Hessian

def xtpl_wrapper(job_type, molecule, xtpl_inputs, xtpl_options, iteration=0):
    """ Create a series of Hessian or Gradient objects for use the extrpolation procedure 
    
    Parameters
    ----------
    job_type: str
    molecule: TemplateFileProcessor.molecule
    xtpl_options: Options
        xtpl_ prefix indicates that this is used to set the 'standard' options from the
        corresponding xtpl_* options here in the creation of a Gradient or Hessian

    Returns
    -------
    lsit[object]
    """
    
    path_additions = ["high_corr", "large_basis", "med_basis", "small_basis"]
    findif_objs = []
    
    for index, inp_file_obj in enumerate(xtpl_inputs):

        # Only two possible programs/success strings
        if index > 0:
            corl_index = -1
        else:
             corl_index = 0
        
        # Three possible energy strings. 1 needs both scf and low correlation energy
        # Make sure energy_regex is a list
        if index == 1:
            energy_regex = xtpl_options.xtpl_energy[1:3]
            split_scf_corl = True
        elif index == 0:
            energy_regex = [xtpl_options.xtpl_energy[0]]
            split_scf_corl = False
        else:
            energy_regex = [xtpl_options.xtpl_energy[1]]
            split_scf_corl = False
        
        # Set specific program and regex strings for specific gradient needed
        # Will be used to create gradient object
        # correction defaults to empty string (yields 0) if nothing found
        options = copy.deepcopy(xtpl_options)
        options.program = xtpl_options.xtpl_programs[corl_index]
        options.success_regex = xtpl_options.xtpl_success[corl_index]
        options.correction_regexes = [xtpl_options.xtpl_corrections.get(f"{abs(corl_index)}", "")]
        options.energy_regex = energy_regex
        options.wait_time = xtpl_options.xtpl_wait_times[index]
 
        if job_type.upper() == 'GRADIENT':
            step_path = f"STEP{iteration:>02d}/{path_additions[index]}"
            grad_obj = Gradient(molecule, inp_file_obj, options, step_path, split_scf_corl)
            findif_objs.append(grad_obj)
        elif job_type.upper() == "HESSIAN":
            path = f"./XTPL/{path_additions[index]}"
            hess_obj = Hessian(options, inp_file_obj, molecule, path, split_scf_corl) 
            findif_objs.append(hess_obj)

    return findif_objs

