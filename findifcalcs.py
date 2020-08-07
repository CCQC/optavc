import itertools
import os
import re
import shutil
import sys
import time
import subprocess
from abc import ABC, abstractmethod

import numpy as np
import psi4

from . import submitter
from .singlepoint import Calculation, SinglePoint
from .utils import time_str_2_sec, get_last_energy
from .submitter import make_sub_script


class FiniteDifferenceCalc(Calculation):

    def __init__(self, molecule, inp_file_obj, options, path="."):

        super().__init__(molecule, inp_file_obj, options, path)
        self.energies = None
        self.result = None
        self.singlepoints = []
        self.failed = []
        self.job_ids = []

    @property
    def ndisps(self):
        return len(self.singlepoints)

    def make_singlepoints(self):
        """ Use psi4's finite difference machinery to create dispalcements and singlepoints """
        ref_molecule = self.molecule.copy()
        ref_path = os.path.join(self.path, "{:d}".format(1))
        ref_singlepoint = SinglePoint(ref_molecule, self.inp_file_obj, self.options, path=ref_path,
                                      num=1, key='reference')
        ref_singlepoint.options.name = f"{self.options.name}-1"
        self.singlepoints.append(ref_singlepoint)

        # Use findifrec to generate directories for each displacement and create a Singlepoint
        # for each
        for disp_num, disp in enumerate(self.findifrec['displacements'].keys()):
            disp_molecule = self.molecule.copy()
            disp_molecule.set_geometry(np.array(self.findifrec['displacements'][disp]['geometry']),
                                       geom_units="bohr")
            disp_path = os.path.join(self.path, "{:d}".format(disp_num + 2)) 
            disp_singlepoint = SinglePoint(disp_molecule, self.inp_file_obj, self.options,
                                           path=disp_path, num=disp_num + 2, key=disp)
            disp_singlepoint.options.name = f"{self.options.name}-{disp_num+2}"
            self.singlepoints.append(disp_singlepoint)

    def get_result(self):
        try:
            return self.result
        except KeyError:
            print("Gradient not yet defined -- did you remember to run compute_gradient() first?")
            raise

    def get_reference_energy(self):
        try:
            return self.findifrec['reference']['energy']
        except KeyError:
            print("Energy not yet computed -- did you remember to run compute_gradient() first?")
            raise

    def sow(self):
        for singlepoint in self.singlepoints:
            singlepoint.write_input()

    def run_individual(self):
        """ Run all singlepoints

        Returns
        -------
        list[str]: list of all job ids that were just run

        """
        return [singlepoint.run() for singlepoint in self.singlepoints]

    def get_energies(self):
        return [sp.get_energy_from_output() for sp in self.singlepoints] 

    @abstractmethod
    def run(self):

        if not self.options.job_array or self.options.cluster.upper() == "SAPELO":
            self.job_ids = self.run_individual()
        else:
            self.options.job_array_range = (1, self.ndisps)
            working_directory = os.getcwd()
            os.chdir(self.path)
            submitter.submit(self.options)
            os.chdir(working_directory)

    @abstractmethod
    def reap(self, force_resub=False):
        """ Once all singlepoints have finished, collect all singlepoints and place in self.findifrec.
        Child classes will use self.findifrec to construct the result

        Raises
        ------
        RuntimeError : if not able to find status of jobs during resub attempt

        """

        while self.collect_failures():
            print(f"1 or more singlepoints have failed, or are still running")
            if self.options.resub:
                self.resub(force_resub)
                force_resub = False  # only try (at most) 1 forced resubmit
                time.sleep(60)  # go to sleep for 1 minute
            else:
                print(f"""\nThe following jobs failed: \n
                        {[singlepoint.disp_num for singlepoint in self.failed]}""")
                break

        for e in self.singlepoints:
            key = e.key
            energy = e.get_energy_from_output()
            if key == 'reference':
                self.findifrec['reference']['energy'] = energy
            else:
                self.findifrec['displacements'][key]['energy'] = energy

    def compute_result(self):
        self.sow()
        self.run()
        return self.reap()

    def resub(self, force_resub=False):
        """ Rerun each singlepoint in self.failed (that has finished) as an individual job. """


        if self.options.cluster.upper() != "SAPELO" or force_resub:
            for singlepoint in self.failed:
                singlepoint.run()  # job_array is now always False for a singlepoint.
        else:
            time.sleep(5)  # ensure that the queue has time to see all jobs
            for job in self.job_ids:
                try:
                    job_status, job_num = FiniteDifferenceCalc.pbs_qstat_info(job)
                except RuntimeError:
                    time.sleep(10)
                    job_status, job_num = FiniteDifferenceCalc.pbs_qstat_info(job)
                    # let RuntimeError go if we still can't find job_state

                if not job_status:
                    continue

                current_sp = self.singlepoints[job_num - 1]
                # self.failed contains any jobs which have not completed successfully check jobs
                # for success
                # some jobs being rerun after success_string is printed add an additional check_status check
                if current_sp in self.failed:

                    # Troubleshooting. Seeing some jobs resubmitted which don't need to be. 
                    # Ensure that self.failed is up to date (should have been updated
                    # immediately before this was called. 
                    # Make sure that self.failed() only contains jobs which have failed rerun.

                    self.collect_failures()
                    if current_sp in self.failed:

                        current_sp.check_status()
                        new_job_id = current_sp.run()
                    
                        # replace job_id with new_job_id to ensure no duplicates
                        self.job_ids[self.job_ids.index(job)] = new_job_id

    def collect_failures(self, raise_error=False):
        """ Collect all jobs which did not successfully exit in self.failed.

        Returns
        -------
        bool: False if unable to find any failures
        
        """

        self.failed = []  # empty self.failed

        if self.failed:
            raise RuntimeError("self.failed was not cleared appropriately")

        for index, singlepoint in enumerate(self.singlepoints):
            # This if statement is only here for testing purposes
            if self.options.resub_test:
                singlepoint.insert_Giraffe()
                if singlepoint.check_resub():
                    self.failed.append(singlepoint)
            # This if statement will be used for most optimizations
            try:
                if not singlepoint.check_status(singlepoint.options.success_regex, return_text=False):
                    self.failed.append(singlepoint)
                elif singlepoint in self.failed:
                    #  Troubleshooting ensure that a successful job cannot persist in self.failed
                    singlepoint.pop(self.failed.index(singlepoint))
            except FileNotFoundError:
                self.failed.append(singlepoint)

        if self.failed:
            if raise_error:
                raise RuntimeError("Found job which has failed")
            return True

        return False

    @staticmethod
    def pbs_qstat_info(job_id, return_stdout=False):
        """  Run PBS/Torque command: qstat -f. Checks job_state for completion.

        Parameters
        ----------
        job_id : str
        return_stdout : bool, optional

        Returns
        -------
        bool : True if job_state is 'C' False otherwise
        int: Translation of Job_Name to displacement number of singlepoint

        Raises
        ------
        RuntimeError : if no match is found for job_state or unable to find job_number

        """

        job_state = False
        pipe = subprocess.PIPE
        process = subprocess.run(['qstat', '-f', f'{job_id}'], stdout=pipe, stderr=pipe)
        output = str(process.stdout)
        # exit_status = re.search(r"\s+exit_status\s=\s(d+)", process.output)

        try:
            completion = re.search(r"\s*job_state\s=\s([A-Z])", output).group(1)
        except AttributeError as e:
            print(f"Could not find job_state in output of qstat -f {job_id}")
            raise RuntimeError from e

        name_itr_num = r"\s*Job_Name\s=\s*[a-zA-Z]*[\_\-\s]?[a-zA-Z]*\d?(\-+\d*)?\-(\d*)"

        try:
            job_num = int(re.search(name_itr_num, output).group(2))
        except AttributeError as e:
            print("\nCould not find displacement number in Job_Name using standard optavc naming convention\n")
            print(output)
            raise RuntimeError from e

        if not completion:
            raise RuntimeError(f"Could not determine state of job {job_id}")
        elif completion == 'C':  # jobs has finished
            job_state = True

        if return_stdout:
            return job_state, job_num, str(process.stdout)
        return job_state, job_num


class Gradient(FiniteDifferenceCalc):
    
    def __init__(self, options, input_obj, molecule, path):
        super().__init__(options, input_obj, molecule, path)
        
        psi4_mol_obj = self.molecule.cast_to_psi4_molecule_object()
        if self.options.point_group is not None:
            psi4_mol_obj.reset_point_group(self.options.point_group)
        self.findifrec = psi4.driver_findif.gradient_from_energy_geometries(psi4_mol_obj)
        self.make_singlepoints()

    def run(self):
        # mpi thing. then call super
        if self.options.mpi:  # compute in MPI mode
            from .mpi4py_iface import master, to_dict, compute
            _singlepoints = to_dict(self.singlepoints)
            self.energies = master(_singlepoints, compute)
            self.energies = [
                float(val[0])
                for val in sorted(self.energies, key=lambda tup: tup[1])
            ]
        else:
            super().run()

    def reap(self, force_resub=False):

        if not self.options.mpi:
            super().reap(force_resub)
        else:
            # no resub, mpi mode.
            for idx, e in enumerate(self.singlepoints):
                key = e.key
                if key == 'reference':
                    self.findifrec['reference']['energy'] = self.energies[idx]
                else:
                    self.findifrec['displacements'][key]['energy'] = self.energies[idx]

        # psi4_mol_obj = self.molecule.cast_to_psi4_molecule_object()
        grad = psi4.driver_findif.compute_gradient_from_energies(self.findifrec)
        self.result = psi4.core.Matrix.from_array(grad)
        return self.result


class Hessian(FiniteDifferenceCalc):

    def __init__(self, options, input_obj, molecule, path):
        super().__init__(options, input_obj, molecule, path)
    
        self.psi4_mol_obj = self.molecule.cast_to_psi4_molecule_object()
        self.findifrec = psi4.driver_findif.hessian_from_energy_geometries(self.psi4_mol_obj, -1)
        self.make_singlepoints()

    def run(self):
        if self.options.name.upper() == 'STEP':
            self.options.name = 'Hess'
        super().run() 

    def reap(self, force_resub=False):

        super().reap(force_resub)

        hess = psi4.driver_findif.compute_hessian_from_energies(self.findifrec, -1) 
        self.result = psi4.core.Matrix.from_array(hess)
        # Could we get the global_option basis? Yes.
        # Would we need to set it, just for this? Yes.
        # Does it mean anything. No, not with our application.
        wfn = psi4.core.Wavefunction.build(self.psi4_mol_obj, 'sto-3g')
        wfn.set_hessian(self.result)
        wfn.set_energy(self.findifrec['reference']['energy'])
        psi4.core.set_variable("CURRENT ENERGY", self.findifrec['reference']['energy'])
        psi4.driver.vibanal_wfn(wfn)
        psi4.driver._hessian_write(wfn)

        return self.result
