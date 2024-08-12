import shutil
import os
import copy

import psi4
import optking

from .molecule import Molecule
from .calculations import AnalyticGradient
from .findifcalcs import Gradient, Hessian
from .xtpl import xtpl_delta_wrapper


class Optimization():
    """ Run AnalyticGradient and Gradient calculations or any procedures which contain and only contain
    those object types """

    def __init__(self, molecule, input_obj, options, xtpl_inputs=None, path='.'):
        
        self.molecule = molecule
        self.options = options
        self.path = os.path.abspath(path)
        self.inp_file_obj = input_obj
        self.step_molecules = []
        self.xtpl_inputs = xtpl_inputs
        self.paths = []  # safety measure. No gradients should share the same path object

    def run(self, restart_iteration=0, user_xtpl_restart=None, path="."):
        """This replicates some of the new psi4 optmize driver """

        # copy step if restart would have overwritten some steps
        self.copy_old_steps(restart_iteration, user_xtpl_restart)

        psi4_mol_obj = self.molecule.cast_to_psi4_molecule_object()
        psi4.core.set_active_molecule(psi4_mol_obj)
        params = psi4.p4util.prepare_options_for_modules()
        optimizer_params = {k: v.get('value') for k, v in params.pop("OPTKING").items() if v.get('has_changed')}

        opt_object = optking.opt_helper.CustomHelper(psi4_mol_obj, params=optimizer_params)            
        initial_sym = psi4_mol_obj.schoenflies_symbol()
        
        for iteration in range(self.options.maxiter):
            # compute the gradient for the current molecule --
            # the path for gradient computation is set to "STEP0x"

            print(f"\n====================Beginning new step {iteration}======================\n") 
            current_sym = psi4_mol_obj.schoenflies_symbol()
            if initial_sym != current_sym:
                psi4_mol_obj.symmetrize(psi4.core.get_local_option("OPTKING", "CARTESIAN_SYM_TOLERANCE"))

                if psi4_mol_obj.schoenflies_symbol() != initial_sym:

                    raise RuntimeError("""Point group changed! (%s <-- %s) You should restart """
                                       """using the last geometry in the output, after """
                                       """carefully making sure all symmetry-dependent """
                                       """input, such as DOCC, is correct.""" % (current_sym, initial_sym))

            # This tells the calling program whether optking is expecting a hessian right now
            opt_calcs = opt_object.calculations_needed()

            # compute or lookup hessian
            if psi4.core.get_option('OPTKING', 'CART_HESS_READ') and (iteration == 0):
                opt_object.params.cart_hess_read = True
                opt_object.params.hessian_file = f"{psi4.core.get_writer_file_prefix(psi4_mol_obj.name())}.hess"
                print(opt_object.params.cart_hess_read)
                print(opt_object.opt_manager.params.cart_hess_read)
            elif 'hessian' in opt_calcs:
                # hessian calculation requested
                if path == '.':
                    path = f'./HESS_{iteration}'

                use_procedure, calc_obj = xtpl_delta_wrapper("HESSIAN", self.molecule, self.options, path)
                if not use_procedure:
                    calc_obj = Hessian(self.molecule, self.inp_file_obj, self.options, path)

                hessian = self.run_calc(iteration, restart_iteration, calc_obj, self.options.resub)
                opt_object.HX = hessian.np

            # Compute gradient
            grad_obj = self.create_opt_gradient(iteration)
            grad = self.run_calc(iteration, restart_iteration, grad_obj, force_resub=self.options.resub)
            ref_energy = grad_obj.get_reference_energy()
            self.step_molecules.append(self.molecule)

            # Pass step data to opt_object
            opt_object.E = ref_energy
            opt_object.gX = grad.np
            opt_object.molsys.geom = psi4.core.get_active_molecule().geometry().np
            psi4.core.print_out(opt_object.pre_step_str())
            opt_object.compute()
            opt_object.take_step()
            psi4.core.print_out(opt_object.post_step_str())

            psi4_mol_obj.set_geometry(psi4.core.Matrix.from_array(opt_object.molsys.geom))
            psi4_mol_obj.update_geometry()
            self.molecule = Molecule(psi4.core.get_active_molecule())            

            # Assess step
            opt_status = opt_object.status()
            if opt_status == 'CONVERGED':
  
                final_energy, final_geom = opt_object.summarize_result()
                psi4_mol_obj.set_geometry(psi4.core.Matrix.from_array(final_geom))
                psi4_mol_obj.update_geometry()

                print('Optimizer: Optimization complete!')
                psi4.core.print_out('\n    Final optimized geometry and variables:\n')
                psi4_mol_obj.print_in_input_format()
                break
            elif opt_status == "FAILED":
                psi4.core.print_out('\n    Final optimized geometry and variables:\n')
                psi4_mol_obj.print_in_input_format()
                print('Optimizer: Optimization failed!')

        if self.options.mpi:
            from .mpi4py_iface import slay
            slay()  # kill all workers before exiting

        print("\n\n OPTIMIZATION HAS FINISHED!\n\n")
        return grad, ref_energy, self.molecule

    def run_calc(self, iteration, restart_iteration, grad_obj, force_resub=True):
        """ run a single gradient for an optimization. Reaping if iteration, restart_iteration,
        and xtpl_reap indicate this is possible

        Parameters
        ----------
        iteration: int
        restart_iteration: int
            indicates (with iteration) whether to sow/run or just reap previous energies
        grad_obj: findifcalcs.Gradient
        force_resub: bool, optional
            If the FIRST reap fails, resubmit all jobs to cluster for any gradient that "should"
            have already been completed based on iteration, restart_iteration, and xtpl_reap

        Returns
        -------
        grad: psi4.core.Matrix

        Notes
        -----
        Reassemble gradients as possible. Always restart based on iteration number
        If the we're rechecking the same input file in xtpl_procedure, xtpl_reap must be set

        """

        try:
            if iteration < restart_iteration:
                result = grad_obj.get_result(force_resub)  # could be 1 or more gradients
            else:
                # self.enforce_unique_paths(grad_obj)
                result = grad_obj.compute_result()
        except RuntimeError as e:
            print(str(e))
            print(f"[CRITICAL] - could not compute {grad_obj.__class__.__name__} at step {iteration}")
            raise
        except FileNotFoundError:
            print(f"Missing an output file: {self.options.output_name}")
            raise
        except ValueError as e:
            print(str(e))
            raise

        return psi4.core.Matrix.from_array(result)

    def create_opt_gradient(self, iteration):
        """  Create Gradient with path and name updated by iteration

        Parameters
        ----------
        iteration: int

        Returns
        -------
        grad_obj : findifcalcs.Gradient

        """

        options = copy.deepcopy(self.options)
        options.name = f"{self.options.name}--{iteration:02d}"
        step_path = f"{self.path}/STEP{iteration:>02d}"

        use_procedure, grad_obj = xtpl_delta_wrapper("GRADIENT", self.molecule, self.options,
                                                     self.path, iteration)

        if not use_procedure:
            if self.options.dertype == 'ENERGY':
                grad_obj = Gradient(self.molecule, self.inp_file_obj, options, path=step_path)
            else:  # DERTYPE == 'GRADIENT'
                grad_obj = AnalyticGradient(self.molecule, self.inp_file_obj, options,
                                            path=step_path)

        return grad_obj

    def copy_old_steps(self, restart_iteration, xtpl_restart):
        """ If a directory is going to be overwritten by a restart copy the directories to backup 
        and prevent steps > restart_iteration are not immediately submitted.  

        """

        dir_test = f'{self.path}/STEP{restart_iteration:0>2d}'
        if xtpl_restart:
            dir_test = f'{dir_test}/low_corr'

        # if only the high_corr exists when restarting and xtpl_restart was not specified,
        # the high_corr jobs will be rurun and a copy of all steps will be made.

        if os.path.exists(dir_test):

            itr = 0
            # determine the number of directories of the form STEPXX exist. What number to
            # start at. itr will exit loop as STEP(Max+1).
            while os.path.exists(f'{self.path}/STEP{itr:>02d}'):
                itr += 1

            restart_itr = 1
            while os.path.exists(f'{self.path}/{restart_itr}_opt'):
                restart_itr += 1
            restart_itr -= 1  # counts too high

            # Move highest indexed group up. Delete. move previous up to replace delete.
            # Delete STEP0X for X >= restart index

            if restart_itr:
                for index in range(restart_itr, 0, -1):  # stop before 0.
                    shutil.copytree(f'{index}_opt',
                                    f'{index + 1}_opt')
                    # copy tree must be able to perform a mkdir for python <= 3.8
                    shutil.rmtree(f'{index}_opt')

            for step_idx in range(itr):
                shutil.copytree(f'{self.path}/STEP{step_idx:>02d}',
                                f'{self.path}/1_opt/STEP{step_idx:>02d}')

                # Keep STEP(restart) if xtpl_restart. Otherwise remove all >= restart_iteration
                if step_idx >= restart_iteration:
                    if step_idx == restart_iteration and xtpl_restart:
                        shutil.rmtree(f'{self.path}/STEP{step_idx:>02d}/low_corr')
                    else:
                        shutil.rmtree(f'{self.path}/STEP{step_idx:>02d}')

            shutil.copyfile(f'{self.path}/output.dat', f'{self.path}/1_opt/output.dat')
            with open(f'{self.path}/output.dat', 'w+'):
                pass  # clear file

    def enforce_unique_paths(self, grad_obj):
        """ Ensure that for an optimization no two gradients can be run in the same directory. Keep
        a list of paths used in a optimization up to date.

        Method should be called whenever a new Gradient in created and before it is run

        Parameters
        ----------
        grad_obj: Gradient
            The newly created Gradient object

        Notes
        -----
        This is a warning for future development: If the gradient's path is not updated with each
        step, collect_failures() will allow new steps to be taken in the same directory. When
        optavc checks the relevant output files, it will find them to be completed and run
        another calculation this will dump new jobs onto the cluster each time.

        Raises
        ------
        ValueError: This should not be caught. Indicates that changes
        """
        if grad_obj.path in self.paths:
            raise ValueError("Gradient's path matches gradient for a previous step. Cannot run. "
                             "This can cause failure in FindifCalc's collect_failures() method")
        else:
            self.paths.append(grad_obj.path)

