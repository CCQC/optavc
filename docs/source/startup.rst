QuickStart
==========

Background and Purpose
----------------------

optavc was originally written by Dr. Copan to facilitate optimizations and hessian calculations by finite difference.
It is primarily meant for internal use by the CCQC on our clusters and computing resources.

optavc is meant to run Psi4, Molpro, Cfour, and Orca QM calculations on the Sapelo and Vulcan clusters. These clusters 
have, over time, utilized the PBS/TORQUE, SLURM, and SGE queuing systems so the submission scripts and cluster
infrastructure should work easily with other clusters of these types. The submission scripts and specific program names
would likely need to be adjusted. Submission scripts for these queuing systems are auto-generated from program specific templates.

Dependencies
------------

python >= 3.6

psi4 >= 1.3.2

Optavc has most recently been tested with Psi4 1.8.2 and Python 3.12

loading psi4
~~~~~~~~~~~~
optavc uses psi4's finite difference module to generate displacements. psi4 must be available in the environment 
as a python module to run optavc. This does not need to be the same version of psi4 that will be run for the actual
calculations.

You can easily add psi4 to your environment with the `vulcan load psi4@master` or `module load PSI4` on Sapelo. 

installing psi4
~~~~~~~~~~~~~~~

If you need to install psi4 and/or a new python: conda is the recommended installation process for dependencies. 
All CCQC members should familiarize themselves with conda and git.

    psi4.1.3.2:: 

        conda create -n <new_env> psi4 psi4-rt -c psi4

    psi4.1.4::

        conda create -n <new_env> psi4 psi4-rt -c psi4/label/dev`

    psi4 1.8::

        conda create -n psi4 mamba -c conda-forge
        mamba install psi4 <anything else you might want> -c conda-forge -c conda-forge/label/libint_dev
        
Installing optavc (for CCQC members)
------------------------------------

There are no planned releases for optavc currently. For development purposes, please fork the GitHub repository using 
the GitHub website. For general usage just clone CCQC/optavc master branch.

clone the GitHub repo to whatever directory you keep python libraries. For instance, in general I recommend::

    mkdir ~/github
    cd ~/github
    git clone https://github.com/CCQC/optavc.git

Please do not install python libraries in `~/bin`. which is for binaries and executables not python modules. 
Please read https://en.wikipedia.org/wiki/Filesystem_Hierarchy_Standard for more information on how the Linux FHS is organized.

add the following line to your `.bashrc` or the rc file for your shell of choice adjust to your shell as:: 

    export PYTHONPATH=$PYTHONPATH:~/github/

Note that optavc's package layout is not the conventional package layout for python projects. If you have to
manually configure your python path for other packages you'd like need to add the repo directory to your `PYTHONPATH` like::

    export PYTHONPATH=$PYTHONPATH:~/github/<package-name>

The import thing is that your environment variable should point to a directory <package-name>
containing the directory (module) with the `__init__.py` file. i.e. for optavc the following file exists::

    export PYTHONPATH=$PYTHONPATH:~/github/optavc/__init__.py

The presence of a `__init__.py` effectively makes the directory its in `optavc`, be "importable" as a module.

Running Optavc
--------------

optavc is, fundamentally, a python module. Therefore there isn't really a input file for optavc. It is generally
easiest to write and then execute a python script in your current working directory.

Basic Requirements:

    a python dict of options (see the options chapter for the bare required options).
    
    a template file. For the purposes of explanation optavc "only" RUNS this template file. The template file must be
    completely sufficient to run whatever singlepoint, gradient, or hessian calculation you are interested in running. 


The easiest way to run optavc is as a background process on the login node of a cluster. This is not ideal, but optavc
spends alot of time sleeping, and is not particularly resource intensive for the kinds of molecules we treat.

To run this way write a simple python script to call optavc like::

    import optavc
    options_kwargs = {
      'template_file_path': "template.dat",
      'energy_regex'      : r"\s*@DF-RHF Final Energy:\s+(-\d+\.\d+)",
      'program'           : "psi4",
      'maxiter'           : 20,
    }
    
    optavc.run_optavc("OPT", options_kwargs)

Then run this python script from cmd line as:: 
    
    nohup python -u <name.py> &

nohup or (no hangup) prevents your process from being terminated by the shell its running in closing. 
nohup places all printing to stdout in nohup.out so all of optavc's output will be placed there. optavc
makes calls to psi4 to perform the finite difference procedure, extrapolations, optimizations etc.
All output produced from psi4 will be placed by default in output.dat

Directories like `HESS` and `STEP00` will be created in the current working directory which contain either input and 
output files or contain directories for each displacement which contain input and output files. Look there to check on
how the calculations themselves are going.

.. autofunction:: optavc.main.run_optavc

Warnings/Changelog - READ THIS!!
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A few important changes and quirks that users should be notified about:

UNITS - defaults to Angstrom. Optavc does not pay attention to the units set in the template file make sure to set units
if Bohr.

SUCCESS REGEXES - The corresponded keyword has been abandoned in favor of using the energy regex as the only indicator
that a job has finished. This is because some programs don't have reliable, consistent success strings. If you're 
worried about your energy regex run a single gradient than `test_input=True` as seen in the documentation above for
`run_optavc`

ENERGY REGEXES - In order to speedup optavc, optavc now run's by default in MULTILINE mode. ENERGY REGEXES must be
matched then **from the beginning of the line** this includes white space.

MEMORY - OPTAVC now only uses `#SBATCH --mem={memory}` for Sapelo submit scripts. Please make sure to determine the total amount
of memory your job uses if using a program such as Molpro which specifies memory in a *per task* fashion.

Reorientation - New keywords `fix_com` and `fix_orientation` have been added. optavc just runs calculations for Psi4 and
fills the results (gradients, energy, etc...) in the correct Psi44 data structures. Since this whole process
is taken care of by Psi4, its normally okay for Psi4 to reorient the molecule (translationally and rotationally) as
it sees fit. The harmonic frequencies will not be affected despite the structure being rotated behind the scenes;
however, the normal mode coordinates will not necessarily align with your molecules. You'd want to visualize the normal
modes with the molecular coordinates Psi4 used (these can be found in output.dat). In geometry optimization, the
final converged geometry you fetch from output.dat will have been rotated by Psi4 as well.

If this behavior is not acceptable (for instance when comparing force constants or gradients numerically against other
programs) you can use the above keywords. When `optavc` creates a Psi4 molecule object, the molecule will not be
allowed to move if these options are specified.

Basic Functionality
~~~~~~~~~~~~~~~~~~~

Optavc can perform optimizations and hessian calculations through Psi4.

Optimizations can be performed with Analytic Gradients or by Finite Differences of Singlepoints

Hessians can be calculated Analytically or by Finite Differences of Gradients or Singlepoints.

Basis set extrapolation and additive corrections can be applied at the level of the Gradient and Hessian.

Aside from the actual calculation of the Energy, Gradient, or Hessian most functionality is obtained
through Psi4 and QCDB.

Finite Difference Displacements are generated by psi4 and calculations for each displacements.
Thermochemical and Vibrational analysis is also performed by Psi4.
Optimization is performed by the Optking python module which comes packages with Psi4 >= 1.7.

