import psi4
from .template import TemplateFileProcessor
from .molecule import Molecule
from .gradient import Gradient
from .mpi4py_iface import slay


class Optimization(object):
    def __init__(self, options):
        template_file_string = open(options.template_file_path).read()
        tfp = TemplateFileProcessor(
            template_file_string, options
        )  # parses a single-point energy input into a molecule object and an input file template
        self.reference_molecule = tfp.molecule  # the units of the molecular geometry contained in the template must be specified by
        self.inp_file_obj = tfp.input_file_object  # options.input_units
        self.options = options
        self.step_molecules = []

    def run(self, restart_iteration=0):
        for iteration in range(self.options.maxiter):
            self.step_molecules.append(self.reference_molecule)
            # compute the gradient for the current molecule -- the path for gradient computation is set to "STEP0x"
            step_path = "STEP{:>02d}".format(iteration)
            grad_obj = Gradient(
                self.reference_molecule,
                self.inp_file_obj,
                self.options,
                path=step_path)
            if iteration >= restart_iteration:
                grad_obj.sow()
                grad_obj.run()
            try:
                grad = grad_obj.reap()
            except:
                raise Exception(
                    "Could not reap gradient at step {:d}".format(iteration))
            # put put the gradient, the energy, and the molecule of the current step in psi::Environment before calling psi4.optking()
            psi4.core.set_gradient(grad)
            psi4.core.set_variable('CURRENT ENERGY',
                                   grad_obj.get_reference_energy())
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
            slay()  #kill all workers before exiting
