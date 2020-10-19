# optavc

In order to run this, you must have Psi4 installed as an importable Python
module.  Instructions can be found on the Psi4 wiki page
[8_FAQ_Contents](https://github.com/psi4/psi4/wiki/8_FAQ_Contents).

This will generate a psi4.so file in /path/to/psi4/obj/bin/, so you must add
that directory to your PYTHONPATH to make Python aware of its existence.

The directory containing this package must also be added to your PYTHONPATH, in
which case the modules are importable as follows.

```python
import optavc.<module name>
```

This version works with latest Psi4 with findif overhaul -jdw 8-31-18

Optavc is designed to run on slurm, pbs_torque, and sge clusters. Due to software issues encountered
by the CCQC singlepoints can be resubmitted if the job fails for any reason. This makes optavc a
rather dangerous tool. When making modifications to optavc watch the pytest suite closely to
ensure that changes have not affected the resubmission code. An error could submit hundreds to
thousands of singlepoints. 

For members of the CCQC, if modifying please make sure to test on all currently used clusters
Sapelo, Vulcan etc... The test suite will detect which cluster you are currently using.


## Recent changes to note for users
In order to speed up restarting large calculations, regexes for fetching energies are used in multiline mode. i.e. Your regex must be set up to match an entire line. Capture groups are still used to isolate the energy.
