import psi4
import os
from typing import Union
#from .dask_iface import connect_Client


class Options(object):
    def __init__(self,
                 template_file_path="template.dat",
                 energy_regex="",
                 success_regex="",
                 fail_regex="",
                 correction_regexes=[],
                 command=None,
                 time_limit=None,
                 program="",
                 input_name="input.dat",
                 files_to_copy=[],
                 output_name="output.dat",
                 input_units="angstrom",
                 point_group=None,
                 submitter=lambda options: None,
                 maxiter=20,
                 job_array=False,
                 mpi=None,
                 queue="",
                 nslots=4,
                 email=None,
                 email_opts='ae',
                 memory="",
                 cluster="",
                 name="",
                 xtpl_templates=None,
                 xtpl_programs=None,
                 xtpl_basis_sets=None,
                 xtpl_success=None,
                 xtpl_energy=None,
                 **psi4kwargs):
        self.template_file_path = template_file_path
        self.energy_regex = energy_regex
        self.correction_regexes = correction_regexes
        self.success_regex = success_regex
        self.fail_regex = fail_regex
        self.time_limit = time_limit
        self.program = program
        self.input_name = input_name
        self.files_to_copy = files_to_copy
        self.output_name = output_name
        self.input_units = input_units
        self.point_group = point_group
        self.submitter = submitter
        self.maxiter = maxiter
        self.mpi = mpi
        self.job_array = job_array
        self.queue = queue
        self.nslots = nslots
        self.job_array_range = None  # needs to be set by calling function
        self.email = email
        self.email_opts = email_opts
        self.memory = memory
        self.cluster = cluster
        self.name = name
        self.xtpl = None # This will be set by xtpl_setter
        self.xtpl_templates = xtpl_templates
        self.xtpl_programs = xtpl_programs
        self.xtpl_basis_sets = xtpl_basis_sets
        self.xtpl_success = xtpl_success
        self.xtpl_energy = xtpl_energy

        if mpi is not None:
            from .mpi4py import compute
            self.command = command
            #self.submitter = compute
        for key, value in psi4kwargs.items():
            key = key.upper()
            psi4.core.print_options()
            if key in psi4.core.get_global_option_list():
                psi4.core.set_global_option(key, value)
                psi4.core.print_out("{:s} set to {:s}\n".format(
                    key,
                    str(value).upper()))
            elif type(value) is dict:
                try:
                    for subkey, subvalue in value.items():
                        subkey = subkey.upper()
                        psi4.core.set_local_option(key, subkey, subvalue)
                        psi4.core.print_out("{:s} {:s} set to {:s}\n".format(
                            key, subkey,
                            str(subvalue).upper()))
                except:
                    raise Exception(
                        "Attempt to set local psi4 option {:s} with {:s} failed."
                        .format(key, str(value)))
            else:
                raise Exception("Unrecognized keyword {:s}".format(str(key)))

    @property
    def xtpl_success(self):
        return self._xtpl_success
    
    @xtpl_success.setter
    def xtpl_success(self, regex_strs: Union[None, list]):
        if regex_strs == None:
            pass
        elif len(regex_strs) != len (self.xtpl_programs):
            raise ValueError("Number of success strings does not match number of programs")
        self._xtpl_success = regex_strs
    
    @property
    def xtpl_energy(self):
        return self._xtpl_energy
    
    @xtpl_energy.setter
    def xtpl_energy(self, energy_strs: Union[None, list]):
        if energy_strs == None:
            pass
        elif len(energy_strs) != 2:
            raise ValueError("Need two regex strings for xtpl calculation")
        self._xtpl_energy = energy_strs
    
    @property
    def xtpl_programs(self):
        return self._xtpl_programs
    
    @xtpl_programs.setter
    def xtpl_programs(self, programs: Union[None, list]):
        if programs == None:
            if self.xtpl == True:
                print("Trying to use standard program")
                self._xtpl_programs = self.program
        elif len(programs) not in [1, 2]:
            raise ValueError("Can not understand the number of programs specified")
        else:
            self._xtpl_programs = programs
    
    @property
    def xtpl_templates(self):
        return self._xtpl_templates
    
    @xtpl_templates.setter
    def xtpl_templates(self, templates: Union[None, list]):
        if templates == None:
            self._xtpl_templates = None
            self._xtpl = False    
        elif len(templates) != 4:
            raise ValueError("Must provide 4 templates files to use basis set extrapolation.")
        for item in templates:
            if templates.count(item) != 1:
                raise ValueError("Template files provided are not unique.")
        else:
            self._xtpl_templates = templates
            self.xtpl = True
    
    @property
    def xtpl_basis_sets(self):
        return self._xtpl_basis_sets
    
    @xtpl_basis_sets.setter
    def xtpl_basis_sets(self, basis_sets: Union[None, list]):
        if basis_sets == None:
            pass
        elif len(basis_sets) != 3:
            raise ValueError("""Improper Number of basis sets. 
                             Optavc can only utilize 3 basis sets currently \
                             with two used for CBS extrapolation""")
        elif basis_sets[0] - basis_sets[1] != 1 or basis_sets[1] - basis_sets[2] != 1:
                raise ValueError("""Improper opterding of basis sets.
                                 Basis sets must be of the form [4, 3, 2] to request a \
                                 [T,Q]Z gradient from a DZ gradient""")
        self._xtpl_basis_sets = basis_sets
