Examples
========

This will be the sole area for optavc examples


Optimizations
-------------


Basic
~~~~~

For the most basic input, only the `program` and `energy_regex` keywords are required.
This tells optavc what program to the inputs generated from `template.dat` with and how
to get the resulting energy from each output.

The regex matches a string that looks like::

        CCSD(T) energy   -123.4567891234

Note that the slashes are required to "escape" the parenthesis so that the
parenthesis are matched as a literal character. The true meaning of the parentheses
in regex is shown below. `(-?\d*\.\d*)`. This matches a string that can or may not contain
a `-` (In QM all our energies should be negative) followed by 0 or more numeric digits,
followed by a dot `.` followed by 0 or more numeric digits. Since we know that there must be
more than 1 digit `\d+` is likely more fitting for the regex but this isn't strictly nessecary for
our purposes. Surrounding these characters in parentheses creates a capture group which allows
optavc to request the value itself from the regex module instead of just the entire line that the
whole regex string matches.

For the sake of the example we set a few more options:
`max_force_g_convergence`: This isn't an optavc keyword, this keyword is sent through optavc
to psi4/optking to control how tightly the geometry is converged. Optavc just runs optking
so all of optking's keywords can be set here in optavc.

`points`: This controls the type of finite difference scheme Psi4 will use. This is an optavc
keyword that is used to control Psi4's internal machinery manually.

.. _BasicExample:

A bare bones input file::

    import optavc

    options = {
        # These two keywords would be sufficient to make OPTAVC run
        'program': 'cfour@2.0+mpi',
        'energy_regex': r"\s*CCSD\(T\)\senergy\s*(-?\d*\.\d*)",
        
        # required to modify psi4
        'max_force_g_convergence': 1e-7,
        'points': 5,

    }

    optavc.run_optavc('OPT', options, restart_iteration=0)

Bad Input
~~~~~~~~~

An input file with uneeded input that few clusters can support well::

    import optavc

    options = {
        # These two keywords would be sufficient to make OPTAVC run
        'program': 'cfour@2.0+mpi',
        'energy_regex': r"\s*CCSD\(T\)\senergy\s*(-?\d*\.\d*)",

        # required to modify psi4
        'max_force_g_convergence': 1e-7,
        'findif_points': 5,

        # These are overiding defaults
        'queue': 'batch_30d',
        'nslots': 8,
        'memory': '92GB',
        'cluster': 'Sapelo'
    }

    optavc.run_optavc('OPT', options, restart_iteration=0)

First there's no need to use the cluster keyword. optavc will autodetect the cluster. Second
If you're gonna be doing finite differences, the cluster will never be able to run so many jobs with these
memory requirements. Computer hours matters just as much as human hours. Analytic Gradients offer better
convergence behavior anyway - see every geometry optimization paper from the 90s. Instead you should try
setting `'dertype': 'hessian'` and reduce the memory requirements as far as possible. You can check how much
memory a job required using the command `sacct -e`

Gradient
~~~~~~~~

.. _GradExample:

optimization using cfour analytic CCSD(T) gradients::

    import optavc
    
    cfour_grad_regex = r"\s*Molecular\s*gradient\s*-+\s*"
    # "([A-Z]+\s#[0-9]+\s[xyz]\s*-?\d+\.\d+\s*)+"
    # This part is not required anymore. Only the header is required.
    
    options = {
        'program': 'cfour@2.0+mpi',
        'template_file_path': 'template.dat',
        'energy_regex': r"\s*CCSD\(T\)\senergy\s*(-?\d*\.\d*)",
        'deriv_regex': cfour_grad_regex,
        'dertype': 'gradient',
        'queue': 'gen6.q',
        'max_force_g_convergence': 1e-7
    }
    
    optavc.run_optavc('OPT', options, restart_iteration=0)

This is an example of how you can use a regex to fetch the gradient from an output file.
In practice there is no need to do this you should use the `deriv_file` keyword. For cfour
this is used automatically and cannot be turned off actually because without the GRD file
the gradient can be rotated strangly and introduce errors in the calculation.

Transition State
~~~~~~~~~~~~~~~~

An example of a transition state optimization followed by frequencies analysis to verify the
stationary point character::

    import optavc
    import os

    os.system(f'cp output.default.hess output.default.{os.getpid().hess}')

    cfour_grad_regex = r"\s*Molecular\s*gradient\s*-+\s*"
    c4_hess = r"\s*Ex\s*Ey\s*Ez"


    options = {
        'program': 'cfour@2.0+mpi',
        'energy_regex': r"\s*CCSD\(T\)\senergy\s*(-?\d*\.\d*)",
        'deriv_regex': cfour_grad_regex,
        'dertype': 'gradient',
        'queue': 'gen6.q',
        'max_force_g_convergence': 1e-7,
        'cart_hess_read': True,
        'opt_type': 'TS'
    }
    
    gradient, energy, molecule = optavc.run_optavc('OPT', options, restart_iteration=0)

    options.update({'deriv_regex': c4_hess,
                    'template_file_path': 'template2.dat',
                    'dertype': 'hessian',
                    'hessian_write': True})

    optavc.run_optavc('HESS', options, molecule=molecule)

There are some optking options left in the input for the second part of this calculation,
psi4 will set these options, but no calls will be made to optking so there's no need to remove them before
the hessian calculation. This really just shows how one can save the molecule from one optavc calculation
and pass it into a second calculation.

Extrapolation
~~~~~~~~~~~~~

.. _XtplExample:

The following example demonstrates a simple two point extrapolation of gradients via singlepoints::

    import optavc

    molpro_ccsdt_regex = r''
    molpro_scf_regex = r''

    options_kwargs = { 
        "program" : "molpro",
        "xtpl_basis_sets" : [[4, 3], [4, 3]],
        "xtpl_energy_regexes" : [[molpro_ccsdt_regex], [[molpro_scf_regex]],
        "xtpl_templates" : [[molpro_qz.dat, molpro_tz.dat], [molpro_qz.dat, molpro_tz.dat]]
    }

    optavc.run_optavc("OPT", options_kwargs)

All other options will resort to default values as described elsewhere. This calculation uses the same
regex for each basis set but different template files. The reverse could also be done: different regexes
for different basis sets but the same input file to run both. Note that the regexes are only input once.
They are broadcast to the expected length so internally the keyword looks like::

        "xtpl_energy_regexes" : [[molpro_ccsdt_regex, molpro_ccsdt_regex], [[molpro_scf_regex, molpro_scf_regex]],

Composite
~~~~~~~~~

A *real* example of a two point mp2 exatrapolation using analytic gradients with a ccsd(t) correction
at a dz basis set where some keywords are expanded more than necessary and some are left to be
broadcast::

    import os
    import optavc
    
    energy_regex = r"\s*\s\sTotal\sEnergy\s*=\s*(-\d*.\d*)"
    mp2_reg = r"\s*DF-MP2\sTotal\sEnergy\s\(a\.u\.\)\s*:\s*(-\d*.\d*)"
    psi4_grad = r"\s*-Total\s*Gradient:\n\s*Atom[XYZ\s]*[-\s]*" # This is just the header i.e.
    ccsdt = r"\s*CCSD\(T\)\senergy\s*(-?\d*\.\d*)"
    c4_grad = r"\s*Molecular\s*gradient\s*-+\s*"
    c4_mp2 = r"\s*The\sfinal\selectronic\senergy\sis\s*(-\d*.\d*)"
    
    options_kwargs = { 
        'program'                 : "psi4@master",
        'maxiter'                 : 100,
        'files_to_copy'           : ['GENBAS'],
        'deriv_regex'             : psi4_grad,
        'nslots'                  : 4,
        'max_force_g_convergence' : 1e-7,
        'ensure_bt_convergence'   : True,
        'xtpl_templates'          : [["mp2_qz.dat", "mp2_tz.dat"], ["scf_qz.dat", "scf_tz.dat"]],
        'xtpl_names'              : [['PR2a_mp2qz', 'PR2a_mp2tz'], ['PR2a_scfqz', "PR2a_scftz"]],
        'xtpl_regexes'            : [[mp2_reg], [energy_regex]],
        'xtpl_dertypes'           : [['gradient'], ['gradient']],
        'xtpl_queues'             : [['gen4.q', 'gen3.q'], ['gen3.q']],
        'xtpl_memories'           : [['30GB', '16GB'], ['16GB', '16GB']],
        'xtpl_basis_sets'         : [[4, 3], [4, 3]],
        'delta_templates'         : [["ccsdpT.dat", "mp2_dz.dat"]],
        'delta_regexes'           : [[ccsdt, c4_mp2]],
        'delta_programs'          : [["cfour@2.0+mpi"]],
        'delta_names'             : [["PR2a_CC", "PR2a_mp2dz"]],
        'delta_deriv_regexes'     : [[c4_grad, c4_grad]],
        'delta_dertypes'          : [['gradient', 'gradient']],
        'delta_parallels'         : [['mpi', 'serial']],
        'delta_memories'          : [['60GB', '30GB']],
        'delta_queues'            : [['gen6.q', 'gen4.q']],
    }
    
    gradient, energy, molecule = optavc.run_optavc('opt', options_kwargs, restart_iteration=0)

Hessians
--------

Basic
~~~~~

Bare bones hessian calculation::

    import optavc

    options = {
        # These two keywords would be sufficient to make OPTAVC run
        'program': 'cfour@2.0+mpi',
        'energy_regex': r"\s*CCSD\(T\)\senergy\s*(-?\d*\.\d*)",
        'findif_points': 5,
        'hessian_write': True
    }

    optavc.run_optavc('HESSIAN', options, sow=True)


Composite
~~~~~~~~~

This is an example of a compsite hessian calculation using analytic hessians from cfour and
analytic gradients in psi4::

    import os
    import optavc
    
    energy_regex = r"\s*\s\sTotal\sEnergy\s*=\s*(-\d*.\d*)"
    mp2_reg = r"\s*DF-MP2\sTotal\sEnergy\s\(a\.u\.\)\s*:\s*(-\d*.\d*)"
    psi4_grad = r"\s*-Total\s*Gradient:\n\s*Atom[XYZ\s]*[-\s]*" # This is just the header i.e.
    ccsdt = r"\s*CCSD\(T\)\senergy\s*(-?\d*\.\d*)"
    c4_mp2 = r"\s*The\sfinal\selectronic\senergy\sis\s*(-\d*.\d*)"
    c4_hess = r"\s*Ex\s*Ey\s*Ez"

    options_kwargs = { 
        'program'                 : "psi4@master",
        'maxiter'                 : 100,
        'files_to_copy'           : ['GENBAS'],
        'deriv_regex'             : psi4_grad,
        'nslots'                  : 4,
        'max_force_g_convergence' : 1e-7,
        'ensure_bt_convergence'   : True,
        'xtpl_templates'          : [["mp2_qz.dat", "mp2_tz.dat"], ["scf_qz.dat", "scf_tz.dat"]],
        'xtpl_names'              : [['PR2a_mp2qz', 'PR2a_mp2tz'], ['PR2a_scfqz', "PR2a_scftz"]],
        'xtpl_regexes'            : [[mp2_reg], [energy_regex]],
        'xtpl_dertypes'           : [['gradient'], ['gradient']],
        'xtpl_queues'             : [['gen4.q', 'gen3.q'], ['gen3.q']],
        'xtpl_memories'           : [['30GB', '16GB'], ['16GB', '16GB']],
        'xtpl_basis_sets'         : [[4, 3], [4, 3]],
        'delta_templates'         : [["ccsdpT.dat", "mp2_dz.dat"]],
        'delta_regexes'           : [[ccsdt, c4_mp2]],
        'delta_programs'          : [["cfour@2.0+mpi"]],
        'delta_names'             : [["PR2a_CC", "PR2a_mp2dz"]],
        'delta_deriv_regexes'     : [[c4_hess]],
        'delta_dertypes'          : [['hessian']],
        'delta_parallels'         : [['mpi', 'serial']],
        'delta_memories'          : [['60GB', '30GB']],
        'delta_queues'            : [['gen6.q', 'gen4.q']],
        'hessian_write'           : True
    }
    
    gradient, energy, molecule = optavc.run_optavc('FREQUENCIES', options_kwargs, sow=True)


Hess-Opt-Hess
~~~~~~~~~~~~~

Final example::

    import optavc
    import os

    cfour_grad_regex = r"\s*Molecular\s*gradient\s*-+\s*"
    c4_hess = r"\s*Ex\s*Ey\s*Ez"


    options = {
        'program': 'cfour@2.0+mpi',
        'energy_regex': r"\s*CCSD\(T\)\senergy\s*(-?\d*\.\d*)",
        'deriv_regex': cfour_hess,
        'dertype': 'hessian',
        'queue': 'gen6.q',
        'max_force_g_convergence': 1e-7,
        'memory': '64GB',
        'hessian_write': True
    }
    
    hessian, energy, molecule = optavc.run_optavc('HESS', options)

    options.update({'deriv_regex': c4_grad_regex,
                    'template_file_path': 'template2.dat',
                    'dertype': 'gradient',
                    'cart_hess_red': True})  # Single PID for entire run no need to copy hessian

    optavc.run_optavc('opt', options, molecule=molecule)

    options.update({"deriv_regex": cfour_grad_regex,
                    "dertype": 'hessian',
                    "template_file_path": 'template.dat'})

    hessian, energy, molecule = optavc.run_optavc('HESS', options)

    


