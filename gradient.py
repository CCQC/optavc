import os
import psi4
import numpy as np
from .dask_iface import run_parallel as rp
from .mpi4py_iface import master, to_dict, compute
from .singlepoint import SinglePoint


class Gradient(object):
    def __init__(self, molecule, inp_file_obj, options, path="."):
        self.molecule = molecule
        self.inp_file_obj = inp_file_obj
        self.options = options
        self.path = os.path.abspath(path)
        self.singlepoints = []
        psi4_mol_obj = self.molecule.cast_to_psi4_molecule_object()
        self.findifrec = psi4.driver_findif.gradient_from_energy_geometries(
            psi4_mol_obj)
        ref_molecule = self.molecule.copy()
        ref_path = os.path.join(self.path, "{:d}".format(1))
        ref_singlepoint = SinglePoint(
            ref_molecule,
            self.inp_file_obj,
            self.options,
            path=ref_path,
            key='reference')
        self.singlepoints.append(ref_singlepoint)
        for disp_num, disp in enumerate(
                self.findifrec['displacements'].keys()):
            disp_molecule = self.molecule.copy()
            disp_molecule.set_geometry(
                np.array(self.findifrec['displacements'][disp]['geometry']),
                geom_units="bohr")
            disp_path = os.path.join(self.path, "{:d}".format(disp_num + 2))
            disp_singlepoint = SinglePoint(
                disp_molecule,
                self.inp_file_obj,
                self.options,
                path=disp_path,
                key=disp)
            self.singlepoints.append(disp_singlepoint)
        self.ndisps = len(self.singlepoints)

    def get_gradient(self):
        try:
            return self.gradient
        except:
            raise Exception(
                "Gradient is not yet defined -- did you remember to run compute_gradient() first?"
            )

    def get_reference_energy(self):
        try:
            return self.energies[0]
        except:
            raise Exception(
                "Energy not yet computed -- did you remember to run compute_gradient() first?"
            )

    def sow(self):
        print('sowing')
        for singlepoint in self.singlepoints:
            singlepoint.write_input()

    def reap(self):
        #self.energies =
        #self.energies = [
        #    singlepoint.get_energy_from_output()
        #    for singlepoint in self.singlepoints
        #]
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
                if key == 'reference':
                    self.findifrec['reference'][
                        'energy'] = e.get_energy_from_output()
                else:
                    self.findifrec['displacements'][key][
                        'energy'] = e.get_energy_from_output()
        print('got to l77')
        psi4_mol_obj = self.molecule.cast_to_psi4_molecule_object()
        self.gradient = psi4.driver.driver_findif.compute_gradient_from_energies(
            self.findifrec)
        #self.gradient = psi4.driver_findif.compute_gradient_from_energies(psi4_mol_obj, self.energies)
        self.gradient = psi4.core.Matrix.from_array(
            self.gradient)  #convert from numpy array to matrix
        return self.gradient

    def run_individual(self):
        for singlepoint in self.singlepoints:
            singlepoint.run()

    def run(self):
        #if False: #self.options.dask: the dask interface doesn't workh
        #    energies = rp(self.singlepoints,self.options.client)
        #    self.energies = energies
        if self.options.mpi:  #compute in MPI mode
            _singlepoints = to_dict(self.singlepoints)
            print('sending energies for gradient ...')
            self.energies = master(_singlepoints, compute)
            self.energies = [
                float(val[0])
                for val in sorted(self.energies, key=lambda tup: tup[1])
            ]
        elif self.options.job_array:
            self.options.job_array_range = (1, self.ndisps)
            working_directory = os.getcwd()
            os.chdir(self.path)
            self.options.submitter(self.options)
            os.chdir(working_directory)
        elif not self.options.job_array:
            self.run_individual()

    def compute_gradient(self):
        self.sow()
        self.run()
        return self.reap()
