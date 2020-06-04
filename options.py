import psi4
import os
from typing import Union
# from .dask_iface import connect_Client


class Options(object):
    def __init__(self, **kwargs):

        self.template_file_path = kwargs.pop("template_file_path", "template.dat")
        self.energy_regex = kwargs.pop("energy_regex", "")
        self.success_regex = kwargs.pop("success_regex", "")
        self.correction_regexes = kwargs.pop("correction_regexes", "")
        self.fail_regex = kwargs.pop("fail_regex", "")
        self.time_limit = kwargs.pop("time_limit", None)
        self.program = kwargs.pop("program", "")
        self.input_name = kwargs.pop("input_name", "input.dat")
        self.files_to_copy = kwargs.pop("files_to_copy", [])
        self.output_name = kwargs.pop("output_name", "output.dat")
        self.input_units = kwargs.pop("input_units", "angstrom")
        self.point_group = kwargs.pop("point_group", None)
        self.maxiter = kwargs.pop("maxiter", 20)
        self.mpi = kwargs.pop("mpi", None)
        self.job_array = kwargs.pop("job_array", False)
        self.queue = kwargs.pop("queue", "")
        self.nslots = kwargs.pop("nslots", 4)
        self.job_array_range = kwargs.pop("job_array", False)  # needs to be set by calling function
        self.email = kwargs.pop("email", None)
        self.email_opts = kwargs.pop("email_opts", 'ae')
        self.memory = kwargs.pop("memory", "")
        self.cluster = kwargs.pop("cluster", "")
        self.name = kwargs.pop("name", "")
        self.resub_job = kwargs.pop("resub_job","")
        self.resub = kwargs.pop("resub_job",False)
        self.xtpl = None  # This will be set by xtpl_setter
        self.xtpl_templates = kwargs.pop("xtpl_templates", None)
        self.xtpl_programs = kwargs.pop("xtpl_programs", None)
        self.xtpl_basis_sets = kwargs.pop("xtpl_basis_sets", None)
        self.xtpl_success = kwargs.pop("xtpl_success", None)
        self.xtpl_energy = kwargs.pop("xtpl_energy", None)
        self.xtpl_corrections = kwargs.pop("xtpl_corrections", None)

        if self.mpi is not None:
            # from .mpi4py import compute

            self.command = kwargs.pop("command")
            # self.submitter = compute
        initialize_psi_options(kwargs)

    @property
    def xtpl_corrections(self) -> Union[tuple, list]:
        return self._xtpl_corrections

    @xtpl_corrections.setter
    def xtpl_corrections(self, vals):
        if vals is None:
            pass
        elif not isinstance(vals, dict) or len(vals) > 2:
            raise ValueError("""Can have at most two corrections for extrapolating gradients of the form
                             {0: "string0"} or {0: r"string0", 1: r"string1"}""")
        self._xtpl_corrections = vals
        

    @property
    def xtpl_success(self):
        return self._xtpl_success
    
    @xtpl_success.setter
    def xtpl_success(self, regex_strs: Union[None, list]):
        if regex_strs is None:
            pass
        elif len(regex_strs) != len (self.xtpl_programs):
            raise ValueError("Number of success strings does not match number of programs")
        self._xtpl_success = regex_strs
    
    @property
    def xtpl_energy(self):
        return self._xtpl_energy
    
    @xtpl_energy.setter
    def xtpl_energy(self, energy_strs: Union[None, list]):
        if energy_strs is None:
            pass
        elif len(energy_strs) != 3:
            raise ValueError("Need three regex strings for xtpl calculation")
        self._xtpl_energy = energy_strs
    
    @property
    def xtpl_programs(self):
        return self._xtpl_programs
    
    @xtpl_programs.setter
    def xtpl_programs(self, programs: Union[None, list]):
        if programs is None:
            if self.xtpl is True:
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
        if templates is None:
            self._xtpl_templates = None
            self._xtpl = False    
        elif len(templates) != 4:
            raise ValueError("Must provide 4 templates files to use basis set extrapolation.")
        else:
            for item in templates:
                if templates.count(item) != 1:
                    raise ValueError("Template files provided are not unique.")
        
            self._xtpl_templates = templates
            self.xtpl = True
    
    @property
    def xtpl_basis_sets(self):
        return self._xtpl_basis_sets
    
    @xtpl_basis_sets.setter
    def xtpl_basis_sets(self, basis_sets: Union[None, list]):
        if basis_sets is None:
            pass
        elif len(basis_sets) != 3:
            raise ValueError("""Improper Number of basis sets. Optavc can only utilize 3 basis sets currently \
                             with two used for CBS extrapolation""")
        elif basis_sets[0] - basis_sets[1] != 1 or basis_sets[1] - basis_sets[2] != 1:
            raise ValueError("""Improper ordering of basis sets. Basis sets must be of the form [4, 3, 2] to request a \
                             [T,Q]Z gradient from a DZ gradient""")
        self._xtpl_basis_sets = basis_sets

    @property
    def resub_job(self):
        return self.resub_job

    @resub_job.setter
    def resub_job(self, job_number):
        self._resub_job = job_number

def initialize_psi_options(kwargs):
    for key, value in kwargs.items():
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
                    "Attempt to set local psi4 option {:s} with {:s} failed.".format(key, str(value)))
        else:
            raise Exception("Unrecognized keyword {:s}".format(str(key)))
