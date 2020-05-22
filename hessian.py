import os
import psi4
import numpy as np
from . import submitter
from .singlepoint import SinglePoint

class Hessian(object):
    def __init__(self, options, input_obj, molecule, path=".", split_scf_corl=False):
        self.molecule = molecule
        self.inp_file_obj = input_obj
        self.options = options
        self.path = os.path.abspath(path)
        self.singlepoints = []
        self.ndisps = None # will be set later
        self.findifrec = None
        self.split_scf_corl = split_scf_corl
        self.scf_hessian = None
        self.make_singlepoints()

    def make_singlepoints(self):
        """ Use psi4's finite diff machinery to create dispalcements and singlepoints """
        psi4_mol_obj = self.molecule.cast_to_psi4_molecule_object()
        self.findifrec = psi4.driver_findif.hessian_from_energy_geometries(psi4_mol_obj, -1)
        if self.split_scf_corl: 
            # create an addition finite difference object for the reference component
            self.scf_findifrec = psi4.driver_findif.hessian_from_energy_geometries(psi4_mol_obj, -1)

        ref_molecule = self.molecule.copy()
        ref_path = os.path.join(self.path, "{:d}".format(1))
        ref_singlepoint = SinglePoint(ref_molecule, self.inp_file_obj, self.options,
                                      path=ref_path, key='reference')
        self.singlepoints.append(ref_singlepoint)

        for disp_num, disp in enumerate(self.findifrec['displacements'].keys()):
            disp_molecule = self.molecule.copy()
            disp_molecule.set_geometry(np.array(self.findifrec['displacements'][disp]['geometry']),
                                       geom_units="bohr")
            disp_path = os.path.join(self.path, "{:d}".format(disp_num + 2))
            disp_singlepoint = SinglePoint(disp_molecule, self.inp_file_obj, self.options, 
                                           path=disp_path, key=disp)
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
                "Energy not yet computed -- did you remember to run compute_hessian() first?")
    def get_scf_reference_energy(self):
        try:
            return self.scf_findifrec['reference']['energy']
        except:
            raise Exception(
                "Energy not yet computed -- did you remember to run compute_hessian() first?")

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
            submitter.submit(self.options)
            os.chdir(working_directory)

    def compute_hessian(self, sow=True):
        if sow:
            self.sow()
            self.run()
        psi4_mol_obj = self.molecule.cast_to_psi4_molecule_object()
        if not self.options.mpi:
            for e in self.singlepoints:
                key = e.key
                energy = e.get_energy_from_output()
                if key == 'reference':
                    self.findifrec['reference']['energy'] = energy[0]
                    if self.split_scf_corl:
                        self.scf_findifrec['reference']['energy'] = energy[1]
                else:
                    self.findifrec['displacements'][key]['energy'] = energy[0]
                    if self.split_scf_corl:
                        self.scf_findifrec['displacements'][key]['energy'] = energy[1]

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

        if self.split_scf_corl:
            scf_hessian = psi4.driver_findif.compute_hessian_from_energies(self.scf_findifrec, -1)
            self.scf_hessian = psi4.core.Matrix.from_array(scf_hessian)
            return self.hessian, self.scf_hessian

        return self.hessian
  
def xtpl_hessian(options, molecule, xtpl_inputs, path=".", sow=True):
    """ Call compute_hessian repeatedly
    """
    from psi4.driver.driver_cbs import corl_xtpl_helgaker_2
    from .xtpl import xtpl_wrapper # circular import fix

    hessians = []
    ref_energies = []

    for index, hess_obj in enumerate(xtpl_wrapper("HESSIAN", molecule, xtpl_inputs, options)):
        hessian = hess_obj.compute_hessian(sow)
        if index == 1:
            scf_hess = hessian[1]
            hessians.append(hessian[0])
            scf_energy = hess_obj.get_scf_reference_energy()
        else:
            hessians.append(hessian)
        ref_energies.append(hess_obj.get_reference_energy())

    hessians.append(scf_hess)
    ref_energies.append(scf_energy)
    basis_sets = options.xtpl_basis_sets
    # Same order as in xtpl_grad()
    low_cbs_hess = corl_xtpl_helgaker_2("basis set xtpl Hess", basis_sets[1], hessians[2], basis_sets[0], hessians[1])
    low_cbs_e = corl_xtpl_helgaker_2("basis set xtpl E", basis_sets[1], ref_energies[2], basis_sets[0],
                                     ref_energies[1])

    # This is, for instance, mp2/[T,Q]Z + CCSD(T)/DZ - mp2/DZ + SCF/QZ
    final_hess = psi4.core.Matrix.from_array(low_cbs_hess.np + hessians[0].np - hessians[3].np + hessians[4].np)
    final_en = low_cbs_e + ref_energies[0] - ref_energies[3] + ref_energies[4]
   
    psi4_mol_obj = hess_obj.molecule.cast_to_psi4_molecule_object()
    wfn = psi4.core.Wavefunction.build(psi4_mol_obj, 'sto-3g')
    wfn.set_hessian(final_hess)
    wfn.set_energy(final_en)
    psi4.core.set_variable("CURRENT ENERGY", final_en)
    psi4.driver.vibanal_wfn(wfn)
    psi4.driver._hessian_write(wfn)

    print(ref_energies)
    print(final_en)

    return final_hess

