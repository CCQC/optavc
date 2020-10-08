
import os
import time
from abc import abstractmethod

import numpy as np
import psi4
from .singlepoint import Calculation, SinglePoint


class FiniteDifferenceCalc(Calculation):
    f""" A Calculation consisting of a series of Singlepoints with needed machinery to submit,
    collect and assemble these Singlepoints.
    
    Attributes
    ----------

    singlepoints: list of Singlepoint
        all singlepoints
    failed: list of Singlepoint
        Singlepoints for which energy could not be found. Singlepoints are added and removed with 
        each collect_failures call
    job_ids: list of str
        collection of job IDs from the cluster. job IDs are added whenever run is called. Removed
        whenever resub is called. Resub will replace an ID if the singlepoint is rerun.
    """

    def __init__(self, molecule, inp_file_obj, options, path="."):

        super().__init__(molecule, inp_file_obj, options, path)
        self.result = None
        self.singlepoints = []  # all singlepoint objects
        self.failed = []  # singlepoints that have failed
        self.job_ids = []
        self.findifrec: object
        self.result: psi4.core.Matrix
        # This essentially defines an abstract attribute. Forces a child class to set these
        # attributes without setting here

    @property
    def ndisps(self):
        return len(self.singlepoints)

    def make_singlepoints(self):
        """ Use psi4's finite difference machinery to create dispalcements and singlepoints """
        ref_molecule = self.molecule.copy()
        ref_path = os.path.join(self.path, "{:d}".format(1))
        ref_singlepoint = SinglePoint(ref_molecule, self.inp_file_obj, self.options, path=ref_path,
                                      disp_num=1, key='reference')
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
                                           path=disp_path, disp_num=disp_num + 2, key=disp)
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
        return [sp.get_energy() for sp in self.singlepoints]

    @abstractmethod
    def run(self):

        self.options.job_array = self.cluster.enforce_job_array(self.options.job_array)

        if not self.options.job_array:
            self.job_ids = self.run_individual()
        else:
            self.options.job_array_range = (1, self.ndisps)
            working_directory = os.getcwd()
            os.chdir(self.path)
            # submit output not captured. Job ID not needed for an array
            self.cluster.submit(self.options)
            os.chdir(working_directory)

    @abstractmethod
    def reap(self, force_resub=False):
        """ Once all singlepoints have finished, collect all singlepoints and place in
        self.findifrec. Child classes will use self.findifrec to construct the result

        Raises
        ------
        RuntimeError : if not able to find status of jobs during resub attempt

        """

        while self.collect_failures():
            if self.options.resub:
                self.resub(force_resub)
                force_resub = False  # only try (at most) 1 forced resubmit
                # use minimum time or user's defined time
                check_every = self.cluster.resub_delay(self.options.sleepy_sleep_time)
                time.sleep(check_every)
            else:
                print(f"""Resub has not been turned on. The following jobs failed: \n
                        {[singlepoint.disp_num for singlepoint in self.failed]}""")
                break

        # This code may only be reached if self.collect_failures() is empty. check_status
        # should have been called many times already.
        for e in self.singlepoints:
            key = e.key
            energy = e.get_energy()
            if key == 'reference':
                self.findifrec['reference']['energy'] = energy
            else:
                self.findifrec['displacements'][key]['energy'] = energy

    def compute_result(self):
        self.sow()
        self.run()
        return self.reap()

    def resub(self, force_resub=False):
        """ Rerun each singlepoint in self.failed as an individual job. """

        if force_resub or self.options.job_array is True:
            # Immediately rerun all failed jobs if singlepoints were previously submitted as an
            # array OR if performing restart and could not reap.
            # Must fill in job_ids to prevent jobs from being resubmitted on next call of resub
            self.job_ids = [singlepoint.run() for singlepoint in self.failed]
            print(f"\nJob IDS for forced resubmit\n{self.job_ids}\n")
            self.options.job_array = False  # once we've resubmitted once. Turn array off
            return

        time.sleep(5)  # ensure that the queue has time to see all jobs

        eliminations = []
        resubmitting = []

        for job in self.job_ids:
            try:
                finished, job_num = self.cluster.query_cluster(job)
            except RuntimeError:
                time.sleep(10)
                finished, job_num = self.cluster.query_cluster(job)
                # let RuntimeError go if we still can't find job_state after second attempt
            if not finished:
                # Jobs are only considered for resubmission if the cluster has marked as finished
                continue

            try:
                current_sp = self.singlepoints[job_num - 1]
                # adjust job_num for zero based counting
            except IndexError:
                print("why is this failing now??")
                print(f"job_number: {job_num}")
                raise

            self.collect_failures()  # refresh list of self.failed
            self.check_resub_count()  # remove singlepoints from self.failed based on resub_max

            if current_sp in self.failed:
                resubmitting.append(current_sp)
                new_job_id = current_sp.run()
                current_sp.resub_count += 1
                # replace job_id with new_job_id to ensure no duplicates
                self.job_ids[self.job_ids.index(job)] = new_job_id
            else:
                # if job is not in failed and has finished remove it after loop is completed.
                eliminations.append(job)

        for job in eliminations:
            self.job_ids.remove(job)

        if resubmitting:
            print("\nThe followin jobs have been resubmitted: ")
            print([singlepoint.disp_num for singlepoint in resubmitting])

    def collect_failures(self, raise_error=False):
        """ Collect all jobs which did not successfully exit in self.failed.

        Returns
        -------
        bool: False if unable to find any failures
        
        """

        # empty self.failed to prevent duplicates. Not using set since removal is necessary
        self.failed = []

        for index, singlepoint in enumerate(self.singlepoints):
            # This if statement is only here for testing purposes
            if self.options.resub_test:
                singlepoint.insert_Giraffe()
                if singlepoint.check_resub():
                    self.failed.append(singlepoint)
            # This if statement will be used for an optimization
            try:
                success = singlepoint.check_status(singlepoint.options.energy_regex,
                                                   return_text=False)
                if not success:
                    self.failed.append(singlepoint)
                elif singlepoint in self.failed:
                    # self.failed was emptied.
                    print("WARNING: self.failed was not purged correctly. Issue has been caught "
                          "and the offending singlepoint has been removed from self.failed")
                    self.failed.pop(self.failed.index(singlepoint))
            except FileNotFoundError:
                self.failed.append(singlepoint)

        if self.failed:
            if raise_error:
                raise RuntimeError("Found job which has failed")
            return True

        return False

    def check_resub_count(self):
        """ Update self.failed to not contain any singlepoints which have already been submitted
        the maximum number of times. """

        if self.failed:
            resub_required = True
        else:
            return

        eliminations = []

        for singlepoint in self.failed:
            if singlepoint.resub_count > self.options.resub_max:
                eliminations.append(singlepoint)

        for singlepoint in eliminations:
            self.failed.remove(singlepoint)

        if resub_required and not self.failed:
            print("The following singlepoints have failed and exceeded resub_max Optavc has "
                  "finished as many singlepoints as possible")
            print([singlepoint.disp_num for singlepoint in eliminations])
            raise RuntimeError("1 or more singlepoints have failed and exceeded the number of"
                               "allowed resubmissions")


class Gradient(FiniteDifferenceCalc):

    def __init__(self, molecule, input_obj, options, path):
        super().__init__(molecule, input_obj, options, path)
        
        self.psi4_mol_obj = self.molecule.cast_to_psi4_molecule_object()
        if self.options.point_group is not None:
            self.psi4_mol_obj.reset_point_group(self.options.point_group)

        create_grad = Gradient.get_psi4_method()[0]
        self.findifrec = create_grad(self.psi4_mol_obj)
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
            # legacy mpi code.
            for idx, e in enumerate(self.singlepoints):
                key = e.key
                if key == 'reference':
                    self.findifrec['reference']['energy'] = self.energies[idx]
                else:
                    self.findifrec['displacements'][key]['energy'] = self.energies[idx]

        # psi4_mol_obj = self.molecule.cast_to_psi4_molecule_object()
        compute_grad = Gradient.get_psi4_method()[1]
        grad = compute_grad(self.findifrec)
        self.result = psi4.core.Matrix.from_array(grad)
        return self.result

    @staticmethod
    def get_psi4_method():
        if '1.4' in psi4.__version__:
            create = psi4.driver_findif.gradient_from_energies_geometries
            compute = psi4.driver_findif.assemble_gradient_from_energies
        else:
            create = psi4.driver_findif.gradient_from_energy_geometries
            compute = psi4.driver_findif.compute_gradient_from_energies
        return create, compute


class Hessian(FiniteDifferenceCalc):

    def __init__(self, molecule, input_obj, options, path):
        super().__init__(molecule, input_obj, options, path)
    
        self.psi4_mol_obj = self.molecule.cast_to_psi4_molecule_object()
        make_hess = Hessian.get_psi4_method()[0]
        self.findifrec = make_hess(self.psi4_mol_obj, -1)
        self.make_singlepoints()

    def run(self):
        if self.options.name.upper() == 'STEP':
            self.options.name = 'Hess'
        super().run() 

    def reap(self, force_resub=False):

        super().reap(force_resub)

        compute_hess = Hessian.get_psi4_method()[1]
        hess = compute_hess(self.findifrec, -1)
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

    @staticmethod
    def xtpl_hessian(molecule, xtpl_inputs, options, path="./HESS", sow=True):
        """ Call compute_hessian repeatedly
        Need to do: (CCSD w/ (T) correction)
                    MP2/QZ, SCF/QZ and MP2/TZ
        """

        from .xtpl import xtpl_wrapper, energy_correction, order_high_low  # circular import fix

        hessians = []
        ref_energies = []

        for index, hess_obj in enumerate(xtpl_wrapper("HESSIAN", molecule, xtpl_inputs, options,
                                                      path)):
            
            # separate_mp2 denotes when a "new" calculation needs to be performed
            if hess_obj.options.xtpl_input_style == [2, 2]:
                separate_idx = 2
            else:
                separate_idx = 1

            hess_obj.options.name = 'hess'

            if index not in [0, separate_idx] or sow is False:
                hessian = hess_obj.reap(force_resub=True)
            else:
                hessian = hess_obj.compute_result()

            hessians.append(hessian)
            ref_energies.append(hess_obj.get_reference_energy())

        basis_sets = options.xtpl_basis_sets
        # Same order as in xtpl_grad()
        
        # xtpl.order_high_low
        ordered_en, ordered_hess = order_high_low(hessians, ref_energies, options.xtpl_input_style)
        
        final_en, final_hess, _ = energy_correction(basis_sets, ordered_hess, ordered_en)

        print("\n\n=============================XTPL-HESS=============================")
        print(f"Energies:\n {ordered_en}")
        print(f"final_energy: {final_en}")
        print(f"final_hess:\n {final_hess.np}")
        print("===================================================================\n\n")

        psi4_mol_obj = hess_obj.molecule.cast_to_psi4_molecule_object()
        wfn = psi4.core.Wavefunction.build(psi4_mol_obj, 'sto-3g')
        wfn.set_hessian(final_hess)
        wfn.set_energy(final_en)
        psi4.core.set_variable("CURRENT ENERGY", final_en)
        psi4.driver.vibanal_wfn(wfn)
        psi4.driver._hessian_write(wfn)

        return final_hess

    @staticmethod
    def get_psi4_method():
        if '1.4' in psi4.__version__:
            create = psi4.driver_findif.hessian_from_energies_geometries
            compute = psi4.driver_findif.assemble_hessian_from_energies
        else:
            create = psi4.driver_findif.hessian_from_energy_geometries
            compute = psi4.driver_findif.compute_hessian_from_energies
        return create, compute
