import psi4
import numpy as np
from .molecule import Molecule
from .gradient import Gradient
from .xtpl import xtpl_wrapper, energy_correction, order_high_low


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
            # compute the gradient for the current molecule --
            # the path for gradient computation is set to "STEP0x"
            print(f"Beginning step {iteration}") 
            if self.options.xtpl:
                # Calls single_grad repeatedly
                print("Calling xtpl_grad")
                ref_energy, grad = self.xtpl_grad(iteration, restart_iteration, xtpl_restart)
            else:
                grad, grad_obj = self.single_grad(iteration, restart_iteration)
                ref_energy = grad_obj.get_reference_energy()
            # put the gradient, energy, and molecule for the current step in psi::Environment
            # before calling psi4.optking()
            try:
                print("Setting gradient and updating molecule")
                print(f"Calling psi4.core.set_gradient {grad.np}")
                psi4.core.set_gradient(grad)
                print(f"Calling psi4.core.set variable energy {ref_energy}")
                psi4.core.set_variable('CURRENT ENERGY', ref_energy)
                psi4_mol_obj = self.reference_molecule.cast_to_psi4_molecule_object()
                if self.options.point_group is not None:  # otherwise autodetect
                    psi4_mol_obj.reset_point_group(self.options.point_group)
                print("Setting legacy molecule")
                psi4.core.set_legacy_molecule(psi4_mol_obj)
                print("Getting exit code and calling optking")            
                optking_exit_code = psi4.core.optking()
                # optking has put the next step geometry in psi::Environment,
                # so we can grab a copy and cast it
                # from psi4.Molecule() to Molecule()
                self.reference_molecule = Molecule(psi4.core.get_legacy_molecule())
                print("Checking exit codes")
                if optking_exit_code == psi4.core.PsiReturnType.EndLoop:
                    psi4.core.print_out("Optimizer: Optimization complete!")
                    break
                elif optking_exit_code == psi4.core.PsiReturnType.Failure:
                    raise Exception("Optimizer: Optimization failed!")
                # We finished a step. Certainly, hessian reading should be disabled now!
                psi4.core.set_local_option('OPTKING', 'CART_HESS_READ', False)
                psi4.core.set_legacy_molecule(None)
            except Exception as e:
                print("An errror was encountered while using psi4 to take a step")
                print(str(e))
                raise RuntimeError from e                
        if self.options.mpi:
            from .mpi4py_iface import slay
            slay()  # kill all workers before exiting

    def single_grad(self, iteration, restart_iteration, inp_file_obj=None, options=None,
                    step_path=None, xtpl_restart=False, grad_obj=None):
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
        xtpl_restart : bool, optional
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
            
            options.name = f"{options.name}--{iteration:02d}"

            grad_obj = Gradient(self.reference_molecule, inp_file_obj, options, step_path)

        # reassemble gradients as possible
        # Always restart based on iteration number
        # Then consider if the we're rechecking the same input file in xtpl procedure

        try:
            if iteration < restart_iteration:
                grad = grad_obj.reap()  # could be 1 or more  gradients
            elif xtpl_restart:
                grad = grad_obj.reap()
            else:
                grad = grad_obj.compute_gradient()
        except RuntimeError as e:
            if xtpl_restart:
                print(str(e))
                print(f"""[CRITICAL] - could not compute gradient at step {iteration} \
                        sub-step {grad_obj.path}""")
            else:
                print(str(e))
                print(f"[CRITICAL] - could not compute gradient at step {iteration}")
            raise
        except FileNotFoundError as e:
            print(f"Missing {self.options.output_name}")
            raise
        except ValueError as e:
            print(e)
            raise

        return grad, grad_obj

    def xtpl_grad(self, iteration, restart_iteration, xtpl_restart=None):
        """ Call single_grad repeatedly using gradient objects from xtpl.xtpl_wrapper
            perform a basis set extrapolation and correlation correction
        """

        gradients = []
        ref_energies = []

        for index, grad_obj in enumerate(xtpl_wrapper("GRADIENT", self.reference_molecule,
                                                      self.xtpl_inputs, self.options, iteration)):

            # [2, 2] -> grab the low correlation, small basis calculations in single input file
            # [1, 3] -> do all low correlation calculations in single output file
            if self.options.xtpl_input_style == [2, 2]:
                separate_mp2 = 2
            else:
                separate_mp2 = 1

            # want to set sow = False if iteration < restart_iteration
            # if index not in [0, 2]
            # if xtpl_restart and index == 0
            acceptable_index = index not in [0, separate_mp2]
            low_corr_restart = xtpl_restart and index == 0 and iteration == restart_iteration

            if acceptable_index or low_corr_restart:
                restart = True
            else:
                restart = False

            grad_obj.options.name = f"{grad_obj.options.name}--{iteration:>02d}"
    
            grad, grad_obj = self.single_grad(iteration, restart_iteration, xtpl_restart=restart,
                                              grad_obj=grad_obj)

            gradients.append(grad)
            ref_energies.append(grad_obj.get_reference_energy())

        basis_sets = self.options.xtpl_basis_sets
        # These are "correlation gradients" i.e. energy_regex should correspond
        # only to correlation energy

        # Different orders for input_styles unify back to high_corr -> low corr large_basis -> small_basis
        ordered_en, ordered_grads = order_high_low(gradients, ref_energies, self.options.xtpl_input_style)
        
        final_en, final_grad, low_CBS_e = energy_correction(basis_sets, ordered_grads, ordered_en)

        print(
            f"\n\n=====================================xtpl=====================================\n")
        print(f"xtpl gradient:\n {str(final_grad.np)}")
        print(f"mp2/tqz{low_CBS_e}\t\t\t using helgaker 2 pt xtpl\n\n")
        print(f"CCSD - mp2 {ref_energies[0] - ref_energies[1]}")
        print(f"xtpl energy: {final_en}")
        print(f"energies {ordered_en}")
        print(f"gradients {[i.np for i in ordered_grads]}")
        print(
            f"\n=====================================xtpl=====================================\n\n")

        return final_en, final_grad
