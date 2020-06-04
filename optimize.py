import psi4
import numpy as np
from .molecule import Molecule
from .gradient import Gradient
from .xtpl import xtpl_wrapper

class Optimization(object):
    def __init__(self, options, input_obj, molecule, xtpl_inputs=None):
       
        self.reference_molecule = molecule
        self.inp_file_obj = input_obj
        self.options = options
        self.step_molecules = []
        self.xtpl_inputs = xtpl_inputs

    def run(self, restart_iteration=0, xtpl_restart=None):
        for iteration in range(self.options.maxiter):    
            self.step_molecules.append(self.reference_molecule)
            # compute the gradient for the current molecule -- the path for gradient computation is set to "STEP0x"
            
            if self.options.xtpl:
                ref_energy, grad = self.xtpl_grad(iteration, restart_iteration, xtpl_restart)  # Call single_grad repeatedly
            else:
                grad, grad_obj = self.single_grad(iteration, restart_iteration)
                ref_energy = grad_obj.get_reference_energy()
            # put put the gradient, the energy, and the molecule of the current step in psi::Environment
            # before calling psi4.optking()
            
            
            # Implement email code here
            # if self.options.email is not None:
                # a
            
            
            
            psi4.core.set_gradient(grad)
            psi4.core.set_variable('CURRENT ENERGY', ref_energy)
            psi4_mol_obj = self.reference_molecule.cast_to_psi4_molecule_object()
            if self.options.point_group is not None:  # otherwise autodetect
                psi4_mol_obj.reset_point_group(self.options.point_group)
            psi4.core.set_legacy_molecule(psi4_mol_obj)
            optking_exit_code = psi4.core.optking()
            # optking has put the next step geometry in psi::Environment, so we can grab a copy and cast it
            # from psi4.Molecule() to Molecule()
            self.reference_molecule = Molecule(psi4.core.get_legacy_molecule())
            if optking_exit_code == psi4.core.PsiReturnType.EndLoop:
                psi4.core.print_out("Optimizer: Optimization complete!")
                break
            elif optking_exit_code == psi4.core.PsiReturnType.Failure:
                raise Exception("Optimizer: Optimization failed!")
            # We finished a step. Certainly, hessian reading should be disabled now!
            psi4.core.set_local_option('OPTKING', 'CART_HESS_READ', False)
        psi4.core.set_legacy_molecule(None)
        if self.options.mpi:
            from .mpi4py_iface import slay
            slay()  # kill all workers before exiting

    def single_grad(self, iteration, restart_iteration, inp_file_obj=None, options=None,
                    step_path=None, split_scf_corl=False, xtpl_restart=None, grad_obj=None):
        """ A standard, single gradient for an optimization.
        Parameters
        ----------
        iteration: int
        restart_iteration: int
            indicates (with iteration) whether to sow/run or just reap previous energies
        inp_file_obj: template.InputFile, optional
            input file for each needed singlepoint
        options: options.Options, optional
        step_path: str, optional
        split_scf_corl: bool, optional
            if true two gradients are returned from reap in order (correlation gradient, scf gradient)
        grad_obj: Object, optional
            if provided overrides everything. Use gradient object for calculation

        Returns
        -------
        tuple
            1 or 2 gradients: psi4.core.Matrix 
            grad_obj: gradient.Gradient
        """

        # Fill in options parameters with class attributes if not provided
        if grad_obj is None:
            if inp_file_obj is None:
                inp_file_obj = self.inp_file_obj
            if options is None:
                options = self.options
            if step_path is None:
                step_path = f"STEP{iteration:>02d}"
             
            grad_obj = Gradient(self.reference_molecule, inp_file_obj, options, step_path, split_scf_corl)

        # reassemble gradients as possible
        # If restart iteration is 5. STEP00 -> O4 should be complete.
        # If restart iteration is  and xtpl_restrt is large_basis. Everything up through STEP05 
        # high_corr should be complete
        try:
            if iteration < restart_iteration or xtpl_restart:
               grad = grad_obj.reap() #could be 1 or more  gradients
            else:    
               grad = grad_obj.compute_gradient()
        except RuntimeError as e:
             if xtpl_restart:
                print(f"[CRITICAL] - could not compute gradient at step {iteration} substep {restart}")
             else:
                print(f"[CRITICAL] - could not compute gradient at step {iteration}")
             raise
        except FileNotFoundError as e:
             print(f"Missing {self.options.output_name}")
             raise

        return grad, grad_obj

    def xtpl_grad(self, iteration, restart_iteration, xtpl_restart=None):
        """ Call single_grad repeatedly using gradient objects from xtpl.xtpl_wrapper
            perform a basis set extrapolation and correlation correction 
       
            Gradients come back in order: ["high_corr", "large_basis", "med_basis", "small_basis"]
            The second gradient "large_basis" comes back as a tuple of the correlation gradient and the scf gradient
            
        """
        from psi4.driver.driver_cbs import corl_xtpl_helgaker_2
        
        gradients = []
        ref_energies = []
        scf_grad, scf_energy = 0, 0

        if xtpl_restart is not None:
            if xtpl_restart not in path_additions:
                raise ValueError(f"""Cannot understand xtpl_restart: {xtpl_restart}.
                                 xtpl_restart must match: {path_additions}""")

        for index, grad_obj in enumerate(xtpl_wrapper("GRADIENT", self.reference_molecule, self.xtpl_inputs, self.options, iteration)):

            # Restart an xtpl_job. If you're trying to go back a few steps
            # just use restart_iteration
            if xtpl_restart is not None:
                if index < path_additions.index(xtpl_restart) and iteration == restart_iteration:
                    restart = path_additions[index]
                else:
                    restart = None
            else:
                restart = None

            grad, grad_obj = self.single_grad(iteration, restart_iteration, xtpl_restart=restart, grad_obj=grad_obj)

            # Save scf gradient and energy till end
            if index == 1:
                scf_grad = grad[1]
                scf_energy = grad_obj.get_scf_reference_energy()
                gradients.append(grad[0])
            else:
                gradients.append(grad)
            ref_energies.append(grad_obj.get_reference_energy())

        gradients.append(scf_grad)
        ref_energies.append(scf_energy)

        basis_sets = self.options.xtpl_basis_sets
        # These are "correlation gradients" i.e. energy_regex should correspond only to correlation energy
        # using order of path additions above ["high_corr", "large_basis", "med_basis", "small_basis", "scf"]
        low_CBS_g = corl_xtpl_helgaker_2("basis set xtpl G", basis_sets[1], gradients[2], basis_sets[0],
                                         gradients[1])
        low_CBS_e = corl_xtpl_helgaker_2("basis set xtpl E", basis_sets[1], ref_energies[2], basis_sets[0],
                                         ref_energies[1])
        # This is, for instance, mp2/[T,Q]Z + CCSD(T)/DZ - mp2/DZ + SCF/QZ
        final_grad = psi4.core.Matrix.from_array(low_CBS_g.np + gradients[0].np - gradients[3].np + gradients[4].np)
        final_en = low_CBS_e + ref_energies[0] - ref_energies[3] + ref_energies[4]
        
        print(f"\n\n=====================================xtpl=====================================\n")
        print(f"xtpl gradient:\n {str(final_grad.np)}")
        print(f"mp2/tqz{low_CBS_e}\t\t\t using helgaker 2 pt xtpl\n\n")
        print(f"CCSD - mp2 {ref_energies[0] - ref_energies[3]}")
        print(f"xtpl energy: {final_en}")
        print(f"energies {ref_energies}")
        print(f"gradients {[i.np for i in gradients]}")
        print(f"\n=====================================xtpl=====================================\n\n")
        
        return final_en, final_grad

