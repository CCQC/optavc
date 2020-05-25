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

    path_additions = ["high_corr", "low_corr"]
    derivative_calcs = []

    # Need to do: (CCSD, (T) correction), MP2
    #             MP2/QZ, SCF/QZ and MP2/TZ
    # reorder energy regex to match internal order above
    ordered_E_regexes = [xtpl_options[0], xtpl_options[4], xtpl_options[1], xtpl_options[2],
                         xtpl_options[5]]
    for index, energy_regex in enumerate(ordered_E_regexes):

        # index can be only 0 or 1 here
        # Only two possible programs/success strings/input files
        if index >= 2:
            corl_index = -1
        else:
            corl_index = 0

        # Set specific program and regex strings for specific gradient needed
        # Will be used to create gradient object
        # correction defaults to empty string (yields 0) if nothing found
        options = copy.deepcopy(xtpl_options)
        options.program = xtpl_options.xtpl_programs[corl_index]
        options.success_regex = xtpl_options.xtpl_success[corl_index]
        inp_file_obj = xtpl_inputs[corl_index]

        if index == 0:
            options.correction_regexes = [xtpl_options.xtpl_corrections]
        options.energy_regex = energy_regex
        options.wait_time = xtpl_options.xtpl_wait_times[corl_index]

        if job_type.upper() == 'GRADIENT':
            step_path = f"STEP{iteration:>02d}/{path_additions[corl_index]}"
            grad_obj = Gradient(molecule, inp_file_obj, options, step_path)
            derivative_calcs.append(grad_obj)
        elif job_type.upper() == "HESSIAN":
            path = f"./XTPL/{path_additions[corl_index]}"
            hess_obj = Hessian(options, inp_file_obj, molecule, path)
            derivative_calcs.append(hess_obj)

    return derivative_calcs


def energy_correction(basis_sets, deriv, ref_energies):
    from psi4.driver.driver_cbs import corl_xtpl_helgaker_2

    low_cbs_hess = corl_xtpl_helgaker_2("basis set xtpl Hess", basis_sets[1], deriv[4],
                                        basis_sets[0], deriv[2])
    low_cbs_e = corl_xtpl_helgaker_2("basis set xtpl E", basis_sets[1], ref_energies[4],
                                     basis_sets[0], ref_energies[2])

    # This is, for instance, mp2/[T,Q]Z + CCSD(T)/DZ - mp2/DZ + SCF/QZ
    final_hess = psi4.core.Matrix.from_array(
        low_cbs_hess.np + deriv[0].np - deriv[1].np + deriv[3].np)
    final_en = low_cbs_e + ref_energies[0] - ref_energies[1] + ref_energies[3]
    return final_en, final_hess, low_cbs_e
