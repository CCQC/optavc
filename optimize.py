import psi4
import numpy as np
import copy
from .template import TemplateFileProcessor
from .molecule import Molecule
from .gradient import Gradient

class Optimization(object):
    def __init__(self, options, submitters):
       
        # Initialization of molecule is based on the first template provided

        if options.xtpl:
            tfps = [TemplateFileProcessor(open(i).read(), options) for i in options.xtpl_templates]
            tfp = tfps[0]
            self.xtpl_templates = [i.input_file_object for i in tfps]
        else:
            template_file_string = open(options.template_file_path).read()
            tfp = TemplateFileProcessor(template_file_string, options)

        # parses a single-point energy input into a molecule object and an input file template
        # the units of the molecular geometry contained in the template must be specified by
        # options.input_units
        self.reference_molecule = tfp.molecule
        self.inp_file_obj = tfp.input_file_object  
        self.options = options
        self.step_molecules = []
        self.submitter = submitters

    def run(self, restart_iteration=0):
        for iteration in range(self.options.maxiter):    
            self.step_molecules.append(self.reference_molecule)
            # compute the gradient for the current molecule -- the path for gradient computation is set to "STEP0x"
            
            if self.options.xtpl:
                ref_energy, grad = self.xtpl_grad(iteration, restart_iteration)  # Call single_grad repeatedly
            else:
                grad, grad_obj = self.single_grad(iteration, restart_iteration)
                ref_energy = grad_obj.get_reference_energy()
            # put put the gradient, the energy, and the molecule of the current step in psi::Environment
            # before calling psi4.optking()
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

    def single_grad(self, iteration, restart_iteration, inp_file_obj=None, xtpl_options=None, submitter=None,
                    split_scf_corl=False):
        """ Standard optimization procedure. Calculate a single gradient

        Parameters
        ----------
        iteration: int
        restart_iteration: int
        inp_file_obj: template.InputFile, optional
        xtpl_options: dict, optional
        submitter: function, optional
        split_scf_corl : bool

        Notes
        -----
        Set standard options using xtpl_programs and give gradient fresh copy of options
        otherwise assign self.options to new name and pass to Gradient"""

        if not inp_file_obj:
            inp_file_obj = self.inp_file_obj
        if not submitter:
            submitter = self.submitter

        if xtpl_options:
            options = copy.deepcopy(self.options)
            options.program = xtpl_options.get("program")
            options.energy_regex = xtpl_options.get("energy") 
            options.success_regex = xtpl_options.get("success")
            step_path = f"STEP{iteration:>02d}/{xtpl_options.get('path_add')}"

            print(f"Using {options.program}")
            print(f"Using {options.energy_regex}")
            print(f"Using {options.success_regex}")
        
        else:
            options = self.options
            step_path = f"STEP{iteration:>02d}"
        
        grad_obj = Gradient(self.reference_molecule, inp_file_obj, options, submitter, step_path, split_scf_corl)
        if iteration >= restart_iteration:
            grad_obj.sow()
            grad_obj.run()
        try:
            grad = grad_obj.reap()
        except:
            raise Exception(
                "Could not reap gradient at step {:d}".format(iteration))
        return grad, grad_obj

    def xtpl_grad(self, iteration, restart_iteration):
        """ Call single_grad for each gradient needed. Subdirectories will be created within STEPXX
        Perform gradient extrapolation
        
        Parameters
        ----------
        iteration: int
        restart_iteration: int

        Notes
        -----
        For each theory level and basis set need a gradient of correlation energies
        For large_basis we need to also get the SCF gradient
        """
        from psi4.driver.cbs_wraper import corl_xtpl_helgaker_2

        path_additions = ["high_corr", "large_basis", "med_basis", "small_basis"]
        ref_energies = [] 
        gradients = []
        scf_grad, scf_energy = 0, 0

        for index, inp_file_obj in enumerate(self.xtpl_templates):

            # Only two possible programs/success strings
            if index > 0:
                opt_index = -1
            else:
                opt_index = 0

            # Three possible energy strings. 1 needs both scf and low correlation energy
            if index == 1:
                energy_regex = self.options.xtpl_energy[1:3]
                split_scf_corl = True
            elif index == 0:
                energy_regex = self.options.xtpl_energy[0]
                split_scf_corl = False
            else:
                energy_regex = self.options.xtpl_energy[1]
                split_scf_corl = False

            # Set specific program and regex strings for specific gradient needed
            # Will be used to create gradient object
            xtpl_options = {"program": self.options.xtpl_programs[opt_index], 
                            "success": self.options.xtpl_success[opt_index],
                            "energy": energy_regex,
                            "path_add": path_additions[index]}

            grad, grad_obj = self.single_grad(iteration, restart_iteration, inp_file_obj, xtpl_options, 
                                              self.submitter[opt_index], split_scf_corl=split_scf_corl)

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
        low_CBS_g = corl_xtpl_helgaker_2("basis set xtpl G", basis_sets[1], gradients[2], basis_sets[2],
                                         gradients[3]).np
        low_CBS_e = corl_xtpl_helgaker_2("basis set xtpl E", basis_sets[1], ref_energies[2], basis_sets[2],
                                         ref_energies[3])
        # This is, for instance, mp2/[T,Q]Z + CCSD(T)/DZ - mp2/DZ + SCF/QZ
        final_grad = psi4.core.Matrix.from_array(low_CBS_g.np + gradients[0].np - gradients[3].np + gradients[4].np)
        final_en = low_CBS_e + ref_energies[0] - ref_energies[3] + ref_energies[4]
        print(f"Energies: {ref_energies}")
        print(f"Gradients: {gradients}")
        return final_en, final_grad

    @property
    def submitter(self):
        return self._submitter

    @submitter.setter
    def submitter(self, submitter_objs):
        if callable(submitter_objs):    
            submitter_objs = [submitter_objs] # only one submitter and its a function as expected
        elif len(submitter_objs) == 2 and self.options.xtpl is False:
            raise ValueError("""Too many submitters for a standard optimization.""")
        self._submitter = submitter_objs

