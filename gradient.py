import os
import time
import numpy as np

import psi4
# from .dask_iface import run_parallel as rp

from .singlepoint import SinglePoint
from .submitter import submit


class Gradient(object):
    def __init__(self, molecule, inp_file_obj, options, path="."):
        self.molecule = molecule
        self.inp_file_obj = inp_file_obj
        self.options = options
        self.path = os.path.abspath(path)
        self.singlepoints = []
        # All set later
        self.energies = None
        self.gradient = None
        self.make_singlepoints()

    def make_singlepoints(self):
        """ Use psi4's finite diff machinery to create dispalcements and singlepoints """
        psi4_mol_obj = self.molecule.cast_to_psi4_molecule_object()
        # Assemble all needed singlepoints
        if self.options.point_group is not None:
            psi4_mol_obj.reset_point_group(self.options.point_group)

        self.findifrec = psi4.driver_findif.gradient_from_energy_geometries(psi4_mol_obj)

        ref_molecule = self.molecule.copy()
        ref_path = os.path.join(self.path, "{:d}".format(1))
        ref_singlepoint = SinglePoint(ref_molecule, self.inp_file_obj, self.options, path=ref_path,
                                      key='reference')
        self.singlepoints.append(ref_singlepoint)

        # Use findifrec to generate directories for each displacement and create a Singlepoint
        # for each
        for disp_num, disp in enumerate(self.findifrec['displacements'].keys()):
            disp_molecule = self.molecule.copy()
            disp_molecule.set_geometry(
                np.array(self.findifrec['displacements'][disp]['geometry']),
                geom_units="bohr")
            disp_path = os.path.join(self.path, "{:d}".format(disp_num + 2))
            disp_singlepoint = SinglePoint(disp_molecule, self.inp_file_obj, self.options,
                                           path=disp_path, key=disp)
            self.singlepoints.append(disp_singlepoint)
        self.ndisps = len(self.singlepoints)

    def get_gradient(self):
        try:
            return self.gradient
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

    def reap(self):
        # if self.options.resub:
            # self.collect_failures()
            # self.rerun_failures()

        if self.options.mpi:
            for idx, e in enumerate(self.singlepoints):
                key = e.key
                if key == 'reference':
                    self.findifrec['reference']['energy'] = self.energies[idx]
                else:
                    self.findifrec['displacements'][key][
                        'energy'] = self.energies[idx]
        if not self.options.mpi:
            for e in self.singlepoints:
                key = e.key
                energy = e.get_energy_from_output()
                if key == 'reference':
                    self.findifrec['reference']['energy'] = energy
                else:
                    self.findifrec['displacements'][key]['energy'] = energy

        psi4_mol_obj = self.molecule.cast_to_psi4_molecule_object()
        self.gradient = psi4.driver.driver_findif.compute_gradient_from_energies(self.findifrec)
        # convert from numpy array to matrix
        self.gradient = psi4.core.Matrix.from_array(self.gradient)

        return self.gradient

    def run_individual(self):
        for singlepoint in self.singlepoints:
            singlepoint.run()
    
    def collect_failures(self):
        self.failed_sp = []
        for singlepoint in self.singlepoints:
            if self.options.resub_test:
                singlepoint.insert_Giraffe()
            if not singlepoint.check_success() or singlepoint.check_resub():
                self.failed_sp.append(singlepoint)

    def rerun_failures(self):
        self.buff = self.options.job_array
        self.options.job_array = False
        for failed_sp in self.failed_sp:
            failed_sp.run()
        self.options.job_array = self.buff

    def run(self):

        if self.options.mpi:  # compute in MPI mode
            from .mpi4py_iface import master, to_dict, compute
            _singlepoints = to_dict(self.singlepoints)
            self.energies = master(_singlepoints, compute)
            self.energies = [
                float(val[0])
                for val in sorted(self.energies, key=lambda tup: tup[1])
            ]
        elif self.options.job_array:
            self.options.job_array_range = (1, self.ndisps)
            working_directory = os.getcwd()
            os.chdir(self.path)
            submit(self.options)
            os.chdir(working_directory)
        elif not self.options.job_array:
            self.run_individual()

    def compute_gradient(self):
        self.sow()
        self.run()
        if self.options.resub:
            self.collect_failures()
            self.rerun_failures()
        if self.options.cluster == 'SAPELO':
            return self.sapelo_gradient_wait()
        else:
            return self.reap()

    def sapelo_gradient_wait(self):
        """ Sapelo will wait for a maximum of 12 hours for a gradient before qutting """
        wait = True
        for i in range(20):
            while wait:
                try:
                    time.sleep(self.options.wait_time)
                    gradient = self.reap()
                    return gradient
                except (RuntimeError, FileNotFoundError) as e:
                    print(str(e))
                    pass
        else:
            # else is attached to for loop if we exceed 20 sleeps its time to stop trying
            raise RuntimeError("Wait time exceeded. Time to quit")
