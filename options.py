import psi4
import os
#from .dask_iface import connect_Client
from .mpi4py_iface import compute


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
                 **psi4kwargs):
        self.template_file_path = template_file_path
        self.energy_regex = energy_regex
        self.correction_regexes = correction_regexes
        self.success_regex = success_regex
        self.fail_regex = fail_regex
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
        if mpi is not None:
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
