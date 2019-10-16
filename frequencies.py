import psi4
from .template import TemplateFileProcessor
from .molecule import Molecule
from .hessian import Hessian


class Frequencies(object):
    def __init__(self, options):
        template_file_string = open(options.template_file_path).read()
        tfp = TemplateFileProcessor(
            template_file_string, options
        )  # parses a single-point energy input into a molecule object and an input file template
        self.reference_molecule = tfp.molecule  # the units of the molecular geometry contained in the template must be specified by
        self.inp_file_obj = tfp.input_file_object  # options.input_units
        self.options = options
        self.step_molecules = []

    def run(self, sow=True):
        hess_obj = Hessian(self.reference_molecule,
                           self.inp_file_obj,
                           self.options,
                           path="HESS")
        hess_obj.compute_hessian(sow=sow)


import psi4
from .template import TemplateFileProcessor
from .molecule import Molecule
from .hessian import Hessian


class Frequencies(object):
    def __init__(self, options):
        template_file_string = open(options.template_file_path).read()
        tfp = TemplateFileProcessor(
            template_file_string, options
        )  # parses a single-point energy input into a molecule object and an input file template
        self.reference_molecule = tfp.molecule  # the units of the molecular geometry contained in the template must be specified by
        self.inp_file_obj = tfp.input_file_object  # options.input_units
        self.options = options
        self.step_molecules = []

    def run(self, sow=True):
        hess_obj = Hessian(self.reference_molecule,
                           self.inp_file_obj,
                           self.options,
                           path="HESS")
        hess_obj.compute_hessian(sow=sow)


import psi4
from .template import TemplateFileProcessor
from .molecule import Molecule
from .hessian import Hessian


class Frequencies(object):
    def __init__(self, options):
        template_file_string = open(options.template_file_path).read()
        tfp = TemplateFileProcessor(
            template_file_string, options
        )  # parses a single-point energy input into a molecule object and an input file template
        self.reference_molecule = tfp.molecule  # the units of the molecular geometry contained in the template must be specified by
        self.inp_file_obj = tfp.input_file_object  # options.input_units
        self.options = options
        self.step_molecules = []

    def run(self, sow=True):
        hess_obj = Hessian(self.reference_molecule,
                           self.inp_file_obj,
                           self.options,
                           path="HESS")
        hess_obj.compute_hessian(sow=sow)

