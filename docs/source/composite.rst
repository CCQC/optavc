Composite Gradients and Hessians
================================

Composite Options
-----------------

There are many combinations of xtpl and delta options possible so a more detailed explanation
of the options for composite calculations are given here than in the Options area.


Option Format
~~~~~~~~~~~~~

.. _XtplOptionFormat:

xtpl options and delta options are provided as a list of lists. With xtpl_option[0] corresponding to the options for each
calculation including post-HF correlation and xtpl_option[1] containing options for the Hartree Fock calculations. The options
in these two lists are given in order of decreasing basis set size. i.e::
    
    "xtpl_templates": [[mp2_qz_template, mp2_tz_template], [hf_qz_template, hf_tz_template]],
    "basis set size": [[4, 3], [4, 3]],
 
For delta options. There may be an arbitrary number of lists each of which should be two dimensional i.e::

    "delta_templates": [[core-valence], [spin-orbit], [dboc]]

Internally, each xtpl and delta option will be expanded to its full length; however, options will be broadcast automatically if
possible. Broadcasting can occur in several ways. 

If no value is given for an xtpl or delta keyword, the corresponding *standard*
option will be used for every calculation in the composite gradient. This may be user provided or can be the default value for the
*standard* option. If a single value is given for a xtpl or delta keyword that single value will be used for every calculation.
If a single value is given for each part of an extrapolation and correction the value will be broadcast across the list.

To demonstrate, the following inputs are all equivalent

input 1::

    molpro_mp2_regex = r''
    molpro_ccsd(t)_regex = r''
    molpro_hf_regex = r''
    
    options = {
        "xtpl_templates": [['mp2_qz.dat', 'mp2_tz.dat'], ['mp2_qz.dat', 'mp2_tz.dat']],
        "xtpl_regexes": [[molpro_mp2_regex], [[molpro_hf_regex]],
        "xtpl_basis_sets": [[4, 3], [4, 3]],
        "xtpl_memories": "12GB",
        "delta_templates": [['AE-mp2.dat', 'FC-mp2.dat'], ['ccsd(t).dat', 'FC-mp2.dat']],
        "delta_regexes": [[molpro_mp2_regex], [molpro_ccsd(t), molpro_mp2_regex]],
        "delta_nslots": [[8], [16, 4]],
        "delta_memories": [['16GB', '8GB'], ['32GB', '8GB']],
    }

    run_optavc("OPT", options)

input 2::
    
    molpro_mp2_regex = r''
    molpro_ccsd(t)_regex = r''
    molpro_hf_regex = r''
    
    options = {
        "xtpl_templates": [['mp2_qz.dat', 'mp2_tz.dat'], ['mp2_qz.dat', 'mp2_tz.dat']],
        "xtpl_regexes": [[molpro_mp2_regex, molpro_mp2_regex], [[molpro_hf_regex, molpro_hf_regex]],
        "xtpl_basis_sets": [[4, 3], [4, 3]],
        "xtpl_nslots": [[4, 4], [4, 4]],
        "xtpl_memories": [['12GB', '12GB'], ['12GB', '12GB']],
        "delta_templates": [['AE-mp2.dat', 'FC-mp2.dat'], ['ccsd(t).dat', 'FC-mp2.dat']],
        "delta_regexes": [[molpro_mp2_regex, molpro_mp2_regex], [molpro_ccsd(t), molpro_mp2_regex]],
        "delta_nslots": [[8, 8], [16, 4]],
        "delta_memories": [['16GB', '8GB'], ['32GB', '8GB']],
    }

    run_optavc("OPT", options)

In the above example. no value was provided for *xtpl_nslots* so the default *nslots* value was used to broadcast to the full form.
For *xtpl_regexes* only one value was given for the correlation and scf portions. These were therefore broadcast across the sublist.
For *delta_regexes* and *delta_nslots* the same broadcast occured, here the sublist defines a correction.
For *xtpl_memories* a single value is given for the entire option so it is broadcast across all lists

*xtpl_names* and *delta_names* are unique in that they have a special and custom default. All other options fall back to 
the corresponding *standard* option if no value is provided.

Required Options
~~~~~~~~~~~~~~~~

To run an extrapolated calculation *xtpl_regexes*, *xtpl_basis_sets*, and *xtpl_templates* are requied keywords.
To run a composite calculation the above three keywords are required as well as *delta_regexes*, and *delta_templates*.
All or None of these calculations must be set or an Error will be raised.

The behavior of the Delta and Xtpl classes is dictated almost entirely from these three keywords. All other keywords 
are for cluster interaction.

**For a given sublist if only 1 value is given for *templates* or *regexes* the other MUST contain two or more
values**. Consider the previous example again::

    molpro_mp2_regex = r''
    molpro_ccsd(t)_regex = r''
    molpro_hf_regex = r''
    

    options = {
        "xtpl_templates": [['mp2_qz.dat', 'mp2_tz.dat'], ['mp2_qz.dat', 'mp2_tz.dat']],
        "xtpl_regexes": [[molpro_mp2_regex], [[molpro_hf_regex]],
        "xtpl_basis_sets": [[4, 3], [4, 3]],
        "xtpl_memories": "12GB",
        "delta_templates": [['AE-mp2.dat', 'FC-mp2.dat'], ['ccsd(t).dat', 'FC-mp2.dat']],
        "delta_regexes": [[molpro_mp2_regex], [molpro_ccsd(t), molpro_mp2_regex]],
        "delta_nslots": [[8], [16, 4]],
        "delta_memories": [['16GB', '8GB'], ['32GB', '8GB']],
    }

    run_optavc("OPT", options)

This calculation is run using the default dertype - "ENERGY". The user should know that molpro will print the ccsd(t) mp2
and hartree fock energies in the same output file in the course of running ccsd(t). This means only a handful of jobs need to
be run 2 for the extrapolation and 3 additional jobs for the corrections instead of 8 total.

The length of *<option>_templates* and *<option>_regexes* will be (in general) inversely proportional. Optavc expects this
even if the full specification is given as in input 2 only a certain number of unique templates and regexes are expected.
This can be overspecified and optavc will run more jobs than necessary but optavc will quit if not enough are provided. 
For the extrapolation portion in the example above two unique calculations are performed based on the unique entires in 
*xtpl_templates*.  mp2_qz.dat is run once. mp2_tz.dat is run once.
*molpro_mp2_regex* and *molpro_hf_regex* are used to get energies from both output files.
Similar behavior occurs for *delta_templates* and *delta_regexes* The lengths of all required options are compared
as a sanity check. For a given sublist if only 1 value is given for *templates* or *regexes* the other MUST contain two or more
values.
