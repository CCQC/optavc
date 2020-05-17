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
        self.submitters = submitters

    def run(self, restart_iteration=0):
        for iteration in range(self.options.maxiter):    
            self.step_molecules.append(self.reference_molecule)
            # compute the gradient for the current molecule -- the path for gradient computation is set to "STEP0x"
            
            if self.options.xtpl:
                ref_energy, grad = self.xtpl_grad(iteration, restart_iteration) # Call single_grad repeatedly
            else:
                grad, grad_obj = self.single_grad(iteration, restart_iteration)
                ref_energy = grad_obj.get_reference_energy()
            # put put the gradient, the energy, and the molecule of the current step in psi::Environment before calling psi4.optking()
            psi4.core.set_gradient(grad)
            psi4.core.set_variable('CURRENT ENERGY', ref_energy)
            psi4_mol_obj = self.reference_molecule.cast_to_psi4_molecule_object()
            if self.options.point_group is not None: #otherwise autodetect
            	psi4_mol_obj.reset_point_group(self.options.point_group)
            psi4.core.set_legacy_molecule(psi4_mol_obj)
            optking_exit_code = psi4.core.optking()
            # optking has put the next step geometry in psi::Environment, so we can grab a copy and cast it from psi4.Molecule() to Molecule()
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
            slay()  #kill all workers before exiting

    def single_grad(self, iteration, restart_iteration, inp_file_obj=None, xtpl_options=None, 
                    submitter=None):
        """
        Standard optimization procedure. Calculate a gradient

        Parameters
        ----------
        iteration: int
        inp_file_obj: Object
            object corresponding to singlepoint template files
        path_addition: str
            sub_directory for basis set extrapolation
        """
        
        # Set standard options using xtpl_programs and give gradient fresh copy of options
        # otherwise assign self.options to new name and pass to Gradient
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
        
        grad_obj = Gradient(self.reference_molecule, inp_file_obj, options, 
                            submitter, step_path)
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
        
        Returns
        -------
        np.ndarray
        
        Notes
        -----
        Two point extrapolation formula:
        Helkier et al https://doi.org/10.1016/S0009-2614(98)00111-0
        Gradient Extrapolation:  
        and doi: 10.10635/5.0004863. by Warden et al 
        """

        path_additions = ["high_corr", "large_basis", "med_basis", "small_basis"]
        ref_energies = [] 
        gradients = []

        for index, inp_file_obj in enumerate(self.xtpl_templates):
            if index > 0:
                opt_index = -1
            else:
                opt_index = 0
        
            # Set specific program and regex strings for specific gradient needed
            # Will be used to create gradient object

            xtpl_options = {"program": self.options.xtpl_programs[opt_index], 
                            "success": self.options.xtpl_success[opt_index],
                            "energy": self.options.xtpl_energy[opt_index],
                            "path_add": path_additions[index]}  

            grad, grad_obj = self.single_grad(iteration, restart_iteration, inp_file_obj, xtpl_options, 
                                        self.submitters[opt_index])
            gradients.append(np.asarray(grad))
            ref_energies.append(grad_obj.get_reference_energy())
        print(f"Energies: {ref_energies}")
        print(f"Gradients: {gradients}")
        xtpl_energy = self.extrapolate(ref_energies)
        xtpl_grad = psi4.core.Matrix.from_array(self.extrapolate(gradients))

        return xtpl_energy, xtpl_grad

    def extrapolate(self, calcs):
        basis_sets = self.options.xtpl_basis_sets
        low_CBS = ((basis_sets[0]**3 * calcs[1] - basis_sets[1]**3 * calcs[2])/ 
                   (basis_sets[0]**3 - basis_sets[1]**3))
        print(f"CBS extrapolation: {low_CBS}")
        print(f"Final quantity: {low_CBS + calcs[0] - calcs[3]}") 
        return low_CBS + calcs[0] - calcs[3]

    @property
    def submitters(self):
        return self._submitters

    @submitters.setter
    def submitters(self, submitter_objs):
        if callable(submitter_objs):    
            submitter_objs = [submitter_objs] # only one submitter and its a function as expected
        elif len(submitter_objs) == 2 and options.xtpl == False:
            raise ValueError("""Too many submitters for a standard optimization.""")
        self._submitters = submitter_objs
