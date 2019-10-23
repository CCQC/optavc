# optavc+mpi quickstart

optavc+mpi is an extension of optavc that modifies how optavc interacts with the queue. Rather than queuing each singlepoint, the whole optavc process is placed in the queue, for a requested N nodes. Once these are allocated, optavc+mpi launches with n MPI processes. One of these runs the optimizer, and the rest compute singlepoint energies. 

## Installing optavc+mpi
The easiest way to get this working is to have your own copy of optavc, and a conda
environment for this purpose.

To do this, go into your `~/.bashrc.ext` and `~/.bash_profile.ext` and remove lines that modify your path to point to `$CCQC` or anything of that nature. If you like, just comment the lines so you have them if you need them in the future. 

#### Creating the conda environment
Next, create a conda environment for `psi4`. Do the following (`$` indicates using the terminal) :

```
$ module load python/3.7-anaconda-2019.07
$ conda create -n optavc+mpi python=3.7 psi4 -c psi4
```
That first line makes `conda` visible to you, and the latter 
creates the conda environment and installs `psi4` while we're at it.
To make sure everything is groovy at this point, enter that conda environment with:
```
$ source activate optavc+mpi
```
>**! Do not** use `conda activate` on NERSC systems! Nothing bad will happen, but  you'll get messages about not being set to use `conda activate`. It's all very confusing, and in the end you'll find that you don't have permissions to fix the problem, so just use `source`.

then run
```
$ which psi4
```


If all is well, you'll see something ending with 
```
$ which psi4
PATH_TO_HOME/.conda/envs/p4env/bin/psi4
```

#### Installing `mpi4py`
Ok, now we need to install `mpi4py`, which is, as you might imagine, MPI for Python. 
What follows is a condensed version of [this tutorial](https://docs.nersc.gov/programming/high-level-environments/python/mpi4py/) from NERSC.

> **!!! DO NOT** use `conda install mpi4py` . Things will fail silently later down the line.

Navigate to your home directory and create a directory called `bin` if you don't have one.
```
$ cd 
$ mkdir bin
$ cd bin
```

Then enter the following commands to properly install `mpi4py`.

```
$ wget https://bitbucket.org/mpi4py/mpi4py/downloads/mpi4py-3.0.0.tar.gz
$ tar zxvf mpi4py-3.0.0.tar.gz
$ cd mpi4py-3.0.0
$ module swap PrgEnv-intel PrgEnv-gnu
$ module unload craype-hugepages2M
$ python setup.py build --mpicc="$(which cc) - shared"
$ python setup.py install
```

#### Clone or Fork optavc+mpi from github
If you don't already have a github account connected to the CCQC group, talk to Dr. Turney. Once you have that, navigate to the CCQC page, and look for the `optavc` repository. If  you plan on contributing back to the development of `optavc`, Fork the repository with the "Fork" button in the top right. Then go to your repository and continue. 

Click the green "Clone or download" button, and copy the link to your clipboard. 

Navigate to your `bin` directory and clone the repository:
```
$ git clone 'https://github.com/CCQC/optavc.git'
```

After entering your github username and password, you're all set!


## Running optavc+mpi
This is largely the same, with a `main.py` and `template.dat` file being used to set up the computation. However, now there is also a file for submitting the whole program to the queueing system, usually called `submit.sh`

#### making `main.py`
The `main.py` file is a little different, and should look something like:

```python
from optavc.mpi4py_iface import mpirun
from optavc.options import Options

options_kwargs = {
 'template_file_path': "template.dat",
 'queue'             : "shared",
 'command'           : "qchem input.dat output.dat", 
 'time_limit'        : "48:00:00", #has no effect, but keep
 'energy_regex'      : r"Total energy in the final basis set =\s+([-.0-9]+)",
 'success_regex'     : r"beer", #no effect, but keep
 'fail_regex'        : r"coffee", #no effect, but keep
 'input_name'        : "input.dat",
 'output_name'       : "output.dat",
 'mpi'               : True, #set to true to use mpi, false to not
 'maxiter'           : 20,
 'findif'            : {'points': 3}, #set to 5 if you want slightly better frequencies
 'optking'           : {'max_force_g_convergence': 1e-7, #tighter than this is not recommended
                              'rms_force_g_convergence': 1e-7,
                       }
                       
options_obj = Options(**options_kwargs)
mpirun(options_obj)
```

The big change here is that the `"program"` keyword has been changed to `"command"`, and should be what you would enter on the command line to run your program. This offers a greater degree of flexibility, as you could, in theory, write a python program to compute a CBS energy and use that for singlepoint energies by choice modifications of `"command"` and `"energy_regex"`. 

> **! NOTE**: I ___highly___ recommend testing your input file and energy regex before running your job. Test the input file by running the computation (with a minimal basis) on Vulcan or Cori. Testing the energy regex is pretty simple if you have a sample output file, e.g. the one you got from testing your input. Just run, in the appropriate directory,
>```
> sed -nE 's/YOUR_REGEX_HERE/\1/g' output.dat
>```
You should see _only_ a floating point number printed out on the command line. Also, that number should be negative!

Other than that, make sure you have the `"mpi"` keyword set to `True`. There are a couple of keywords that no longer do anything but are still required in the input. We're working on it! 

#### making `submit.sh`
This file is used to reserve a certain number of nodes for a given period of time. It should look something like,
```bash
#!/bin/bash
#SBATCH --constraint=haswell
#SBATCH -N NNODES
#SBATCH --qos=debug
#SBATCH --time=00:30:00

module load python/3.7-anaconda-2019.07
source activate psi4
module load qchem

srun -n nprocs -c ncores python -u main.py &
wait
```
Make sure to replace `NNODES` with the number of nodes you want, `nprocs` with the number of MPI processes you want to run, and `-ncores` with the number of logical cores you want to allocate to each process. Note that this overdetermines the job allocation requirements, as 64*`NNODES`$ <= `nprocs`*`ncores`

Also, be sure to replace `module load qchem` with the appropriate module for your job. 

> **! NOTE** It is also ___highly___ recommended to run your computation on the `debug` queue before moving to `regular`. The queue time is very short, and you will feel silly if you discover a minor bug after you wait a week in the queue for `regular`. Again, use a minimal basis - you want to take at least one optimization step in 30 minutes to check that the energy regex is working correctly and so on.

Finally, run
```
sbatch submit.sh
``` 
and we're off to the races! 

