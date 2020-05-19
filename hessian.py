import os
import psi4
import numpy as np
from .singlepoint import SinglePoint


class Hessian(object):
    def __init__(self, molecule, inp_file_obj, options, path="."):
        self.molecule = molecule
        self.inp_file_obj = inp_file_obj
        self.options = options
        self.path = os.path.abspath(path)
        self.singlepoints = []
        psi4_mol_obj = self.molecule.cast_to_psi4_molecule_object()
        if self.options.point_group is not None:
            psi4_mol_obj.reset_point_group(self.options.point_group)
        self.findifrec = psi4.driver_findif.hessian_from_energy_geometries(
            psi4_mol_obj, -1)
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

    def get_hessian(self):
        try:
            return self.hessian
        except:
            raise Exception(
                "Hessian is not yet defined -- did you remember to run compute_hessian() first?"
            )

    def get_reference_energy(self):
        try:
            return self.findifrec['reference']['energy']
        except:
            raise Exception(
                "Energy not yet computed -- did you remember to run compute_hessian() first?"
            )

    def sow(self):
        for singlepoint in self.singlepoints:
            singlepoint.write_input()

    def reap(self):
        return [
            singlepoint.get_energy_from_output()
            for singlepoint in self.singlepoints
        ]

    def run_individual(self):
        for singlepoint in self.singlepoints:
            singlepoint.run()

    def run(self):
        if not self.options.job_array:
            self.run_individual()
        else:
            self.options.job_array_range = (1, self.ndisps)
            working_directory = os.getcwd()
            os.chdir(self.path)
            self.options.submitter(self.options)
            os.chdir(working_directory)

    def compute_hessian(self, sow=True):
        if sow:
            self.sow()
            self.run()
        psi4_mol_obj = self.molecule.cast_to_psi4_molecule_object()
        if not self.options.mpi:
            for e in self.singlepoints:
                key = e.key
                if key == 'reference':
                    self.findifrec['reference'][
                        'energy'] = e.get_energy_from_output()
                else:
                    self.findifrec['displacements'][key][
                        'energy'] = e.get_energy_from_output()
        self.hessian = psi4.driver_findif.compute_hessian_from_energies(
            self.findifrec, -1)
        self.hessian = psi4.core.Matrix.from_array(self.hessian)
        # Could we get the global_option basis? Yes.
        # Would we need to set it, just for this? Yes.
        # Does it mean anything. No, not with our application.
        wfn = psi4.core.Wavefunction.build(psi4_mol_obj, 'sto-3g')
        wfn.set_hessian(self.hessian)
        wfn.set_energy(self.findifrec['reference']['energy'])
        psi4.core.set_variable("CURRENT ENERGY",self.findifrec['reference']['energy'])
        psi4.driver.vibanal_wfn(wfn)
        psi4.driver._hessian_write(wfn)
        return self.hessian
