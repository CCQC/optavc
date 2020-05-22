import optavc

# This is an example of a CCSD(T) correction to a mp2/[TQ]Z hessian
# Note that programs, energy_regex, success_regex etc are blank
# xtpl_ counterparts should be filled in instead

# Four templates are required
# To use we need three energy_regexes 1 for the CCSD/DZ correlation energy,
# mp2 correlation energy and scf energy
# the mp2 string here is written to grab either a DF-MP2 correlation energy (used in the [T,Q]Z
# singlepoints and a conventional mp2 energy used for the DZ calculation.

# 1 or 2 programs strings are required
# 1 or 2 success strings are required. If just using psi4 use psi4's driver_cbs
# The two above keywords must match

options_kwargs = {
    'queue'              : "gen4.q,gen6.q",
    'input_name'         : "input.dat",
    'output_name'        : "output.dat",
    'maxiter'            : 100,
    'job_array'          : True,
    'print'              : 3,
    'max_force_g_convergence': 1e-6,
    'ensure_bt_convergence': True,
    'xtpl_templates'     : ["template1.dat", "template2.dat", "template3.dat", "template4.dat"],
    'xtpl_programs'      : ["molpro@2010.1.67+mpi", "psi4@master"],
    'xtpl_energy'        : [r"UCCSD\s*correlation\s*energy\s+(-?\d+\.\d+)",
                            r"\s+M?P?2?\s+Correlation\sEnergy\s*\(?a?\.?u?\.?\)?\s+=?:?\s*(-\d*.\d*)\s*\[?E?h?\]?",
                            r"\s+\s+Reference\sEnergy\s*=\s*(-\d*.\d*)\s+\[Eh\]"],
    'xtpl_corrections'   : {"0": r"\s*Triples\s*\(T\)\s*contribution\s+(-\d*.\d*)"}, 
    'xtpl_success'       : [r"Variable\smemory\sreleased", r"beer"],
    'xtpl_basis_sets'    : [4, 3, 2]
}

# As usual restart_iteration means we should being sowing gradients at STEP5
# xtpl_restart here indicates that we will reap 'high_corr' and sow 'large_basis'

optavc.run_optavc("OPT", options_kwargs, restart_iteration=5, xtpl_restart='large_basis')
