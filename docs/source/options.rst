Options
=======

Options Breakdown
-----------------

Most of the keywords in optavc have reasonable defaults. There are only two keywords that you'll need to specify.

The required keywords are

* `energy_regex` 
	This is the regex string used to match **AND** fetch the energy from one of the output files
* `program`
	optavc has a built-in set of rules for what programs to expect on a given cluster so
	usually requesting `psi4` or `cfour` is sufficient. You should however check that the intended
	build of cfour (for instance) is being used in the generated submit scripts

See the first example for a simple input file like this: :any:`A Basic Example <BasicExample>`

The Basic Options
~~~~~~~~~~~~~~~~~

These are the options that affect what files, templates, and programs that `optavc` uses
to perform calculations and how to retrieve those results.

* `energy_regex`
	regex string that matches the energy printout
* `correction_regexes`
	regex string to fetch an additive correction for instance the (T) correlation energy
* `deriv_regex`
	regex string to capture the values of the gradient. Should be written to match a few lines preceding
	the actual gradient. Optavc has its own regex string with the appropriate capture groups to get the actual
	gradient values. See :any:`An Analytic Gradient Example <GradExample>` for more details. 
* `program`
	name of the program to use to run each displacement.
* `template_file_path`
	Where to get the template file (zmat, input.dat, template.dat) with the molecule and job
	specification to run the calculations. This file does need to contain a cartesian geometry which will be used as
	the reference geometry for generating displacements from. Each displaced geometry will be substituted back into
	a copy of the template file to be run on the cluster. Defaults to `./template.dat`
* `backup_template`
	This is a secondary template that can be used in place of `.template.dat` in case of a restart.
	See keyword documentation below for more details.
* `input_name`
	What to name the generated input files
* `output_name`
	What to name the output files for each displaced calculation
* `input_units`
	What units were used in the template file. This needs to be know so that the geometry is
	interpreted correctly before a psi4 molecule is created
* `deriv_file`
	Name of the file that will contain the desired gradient or hessian. Writing these files may need
	to be turned on manually in your template file. See :any:`An Analytic Gradient Example <GradExample>`
	for more details.
* `files_to_copy`
	Additional files like GENBAS that need to be copied to the compute node where your jobs are run

More Optavc Options
~~~~~~~~~~~~~~~~~~~

More options to control how the geometry optimization or finite differences is performed, how jobs
are submitted (and resubmitted), etc... 

* `point_group`
	optavc will attempt to keep the molecule in this point group
* `dertype`
	What type of calculation should be performed by the finite difference scheme. `energy`, `gradient`, or
	`hessian`. If `hessian` or `gradient` is requested the calculation may not required finite differences at all. Yay!
* `fix_com`
	Don't let Psi4 translate the molecule
* `fix_orientation`
	Don't let Psi4 rotate the molecule
* `points`
	What point scheme to use for finite differences ['3', '5'].
* `job_array`
	Whether to submit the displacements as an array job or individually. This makes no difference don't bother 
* `resub`
	Whether to resubmit jobs that have finished but no matches for `energy_regex` can be found
* `resub_max`
	Maximum number of times a single job can be resubmitted. This should prevent runaway job submissions.
* `sleepy_sleep_time`
	The frequency with which optavc will request an update on the status of its calculations.
* `maxiter`
	How many iterations to allow for a geometry optimization (supersedes optking's `geom_maxiter`)
* `parallel`
	Type of parallelization to use. This can affect the specific program module that is loaded behind
	the scenes in the submission script.
* `cluster`
	This is the name of the cluster you're working with ['Vulcan', 'Sapelo']. This is not required.

Cluster Options
~~~~~~~~~~~~~~~

These options are primarily relevant for running on Sapelo. Vulcan has far fewer configuration options accessible
in the submit scripts. On Vulcan jobs are expected to take up a complete node. On Sapelo this is NOT the case.
You should use as small a resource allocation as possible. Check the output file for resource usage printouts or
use `sacct -e`. The slurm documentation may be helpful for understanding these keywords and you should checkout
the auto-generated documentation below for more information as well. See :any:`Auto-generated Options Docs <OptionsAutodoc>` for more details. 

* `constraint`
	This string is used on the Sapelo cluster to request specific features or node types for your
	jobs
* `nslots`
	How many mpi processes or threads to use
* `threads`
	experimental setting both nslots and threads requests `nslots` mpi tasks each with `threads` omp threads
* `scratch`
	One of ['lscratch', 'scratch']. Defaults to `'scratch'` which is the network Filesystem shared by all nodes.
	`'lscratch'` refers to physical disk space of a physical compute node.
* `time_limit`
	An upper limit estimate of how long the job might run for.
* `queue`
	Relevant for Vulcan and Sapelo. Which set of nodes to submit the jobs to
* `email`
	Whether or not to send an email to the user with job information or updates (goes to your myid automatically)
* `email_opts`
	Controls in what cases to send an email
* `memory`
	How much memory your job can use
* `name`
	The name given to your jobs on the cluster queuing system

Xtpl and Delta Options
~~~~~~~~~~~~~~~~~~~~~~

This section contains keywords to control how singlepoints and gradients should be extrapolated to the complete
basis set and additively corrected. The keywords here are generalizations and of the keywords above for the Cluster
and for general optavc keywords but are applied to each sub calculation in the xtpl and delta framework. Only the
keywords are documented here please read this section for more details about how the keywords can be input and
broadcast. :any:`Extrapolation Options <XtplOptionFormat>`. See :any:`Autogenerated Options Docs <OptionsAutodoc>` for the exact data types each keyword accepts.

* `xtpl_basis_sets`
	The cardinal numbers used for the extrapolation process [[3, 4, 5], [3, 4]] (e.g.)
	[[HF], [Correlated]] 
* `xtpl_templates`
	Template files for different basis set calculations. See examples and autodocs below
	for more details :any:`Autogenerated Options Docs <OptionsAutodoc>`
* `xtpl_regexes`
	Regexes to get gradients or energies corresponding to different basis set calculations.
	See examples and autodocs below for more details. :any:`Auto-generated Options Docs <OptionsAutodoc>`
* `xtpl_programs`
	Can be left blank if `program` should be provided everywhere.
* `xtpl_names`
	individual names for each calculation
* `xtpl_dertypes`
	individual calculation types (energy, gradient, or hessian) for each basis set
* `xtpl_queues`
	individual queues to submit each basis set type to.
* `xtpl_nslots`
	how many tasks or threads to use for each basis set calculation.
* `xtpl_memories`
	how much memory to use for each basis set calculation.
* `xtpl_parallels`
	what type of parallelization to use for each calculation
* `xtpl_scratches`
	what type of scratch to use for each basis set calculation
* `xtpl_deriv_regexes`
	what regex to use to get a gradient or hessian for each basis set calculation
* `scf_xtpl`
	Whether to extrapolate the scf part or just the correlated calculation.

For each `xtpl_<option>` there should be an analogous `delta_<option>`. The `delta_<option>` options use
a different format however see :any:`Extrapolated Extrapolation Options <XtplOptionFormat>` for more information.

The Options class
-----------------

.. _OptionsAutodoc:

.. autoclass:: optavc.options.Options

