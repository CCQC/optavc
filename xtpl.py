import copy
from abc import abstractmethod

import numpy as np
from psi4.core import Matrix
from psi4.driver import driver_cbs

from .template import TemplateFileProcessor
from .findifcalcs import Gradient, Hessian
from .calculations import Calculation, AnalyticGradient


class Procedure(Calculation):
    """ A procedure may be thought of as a list of Calculations and a list of instructions 'SOW'
    and 'REAP' to enable calculating a series of Calculations """

    def __init__(self, job_type, molecule, procedure_options, path="./HESS", iteration=0):

        super().__init__(molecule, procedure_options, path)

        self.job_type = job_type
        self.iteration = iteration

        self.procedure_options = self.flatten_procedure_options()
        self.proc_inputs = self._create_input_files()
        self.procedure = Procedure._reap_sow_ordering(self.procedure_options[1])
        self.calc_objects = self._create_calc_objects()

        self.energy = None
        self.result = None

    @abstractmethod
    def flatten_procedure_options(self):
        pass

    def _create_calc_objects(self):
        """ Use all the options for the procedures many calculations and Procedure attributes to
        create all the needed Calculation objects for a series of Calculations """

        calc_objects = []

        for calc_itr in range(len(self.procedure)):

            options = copy.deepcopy(self.options)

            standard_opt_list = [options.energy_regex, options.template_file_path, options.dertype,
                                 options.program, options.parallel, options.queue, options.name,
                                 options.scratch, options.nslots, options.memory,
                                 options.time_limit]

            for option_itr, calc_option_list in enumerate(self.procedure_options):
                standard_opt_list[option_itr] = calc_option_list[calc_itr]

            calc_path = f"{self.path}/STEP{self.iteration:>02d}/{options.name}"
            input_file = self.proc_inputs[calc_itr]

            if self.job_type == 'HESSIAN':
                # Hessian will make decision within the class how to compute itself
                calc_objects.append(Hessian(self.molecule, input_file, options, calc_path))
            else:
                # for optimization decide now how to compute the gradient
                if options.dertype[calc_itr] == 'GRADIENT':
                    calc_objects.append(
                        AnalyticGradient(self.molecule, input_file, options, calc_path))
                else:
                    calc_objects.append(Gradient(self.molecule, input_file, options, calc_path))

        return calc_objects

    def _create_input_files(self):
        """ Create list of InputFile objects for each calculation from templates
        Returns
        -------
        List[template.InputFile]

        """

        templates = self.procedure_options[1]
        template_strings = [open(template).read() for template in templates]
        xtpl_inputs = [TemplateFileProcessor(template, self.options) for template in
                       template_strings]
        return xtpl_inputs

    def _reap_sow_ordering(self):
        """ Create a list detailing what calculations must be run and which may be reaped from a
        previously run calculation. Template names are just strings check for equality to find
        if a template should have already been run

        Returns
        -------
        List[str]

        """
        templates = self.procedure_options[1]
        procedure = []
        for proc_itr, template in enumerate(templates):
            # slice to find if template has already been seen by loop
            if template in templates[:proc_itr]:
                procedure.append('REAP')
            else:
                procedure.append('SOW')
        return procedure

    def run(self):
        return [calc.run() for calc in self.calc_objects]

    def reap(self, force_resub=False):
        return [calc.reap(force_resub) for calc in self.calc_objects]

    def get_energies(self):
        return [calc.get_reference_energy() for calc in self.calc_objects]

    def get_reference_energy(self):
        """ Called reference to match findif method name reference in terms of displacements """
        return self.energy

    def get_result(self):
        return self.result

    @abstractmethod
    def compute_result(self):
        pass

    def psi4_hessian(self):
        psi4_mol_obj = self.molecule.cast_to_psi4_molecule_object()
        Hessian.psi4_frequencies(psi4_mol_obj, self.result, self.energy)


class Xtpl(Procedure):

    def __init__(self, job_type, molecule, procedure_options, path="./HESS", iteration=0):
        self.xtpl_option_list = [procedure_options.xtpl_regexes,
                                 procedure_options.xtpl_templates,
                                 procedure_options.xtpl_dertypes,
                                 procedure_options.xtpl_programs,
                                 procedure_options.xtpl_parallels,
                                 procedure_options.xtpl_queues,
                                 procedure_options.xtpl_names,
                                 procedure_options.xtpl_scratches,
                                 procedure_options.xtpl_nslots,
                                 procedure_options.xtpl_memories,
                                 procedure_options.xtpl_time_limits]
        super().__init__(job_type, molecule, procedure_options, path, iteration)

    def flatten_procedure_options(self):
        return [xtpl_option[0] + xtpl_option[1] for xtpl_option in self.xtpl_option_list]

    def compute_result(self):

        # psi4 only has a two point extrapolation technique for correlation energy currently
        results = self.reap()
        energies = self.get_energies()

        corr_result = driver_cbs.corl_xtpl_helgaker_2(f"{self.job_type}",
                                                      zLO=self.options.xtpl_basis_sets[0][1],
                                                      valueLO=results[1],
                                                      zHI=self.options.xtpl_basis_sets[0][0],
                                                      valueHI=results[0])
        corr_energy = driver_cbs.corl_xtpl_helgaker_2("energies",
                                                      zLO=self.options.xtpl_basis_sets[0][1],
                                                      valueLO=energies[1],
                                                      zHI=self.options.xtpl_basis_sets[0][0],
                                                      valueHI=energies[0])
        if len(results) == 5:
            scf_result = driver_cbs.scf_xtpl_helgaker_3(f"{self.job_type}",
                                                        zLO=self.options.xtpl_basis_sets[1][-1],
                                                        valueLO=results[-1],
                                                        zMD=self.options.xtpl_basis_sets[1][-2],
                                                        valueMD=results[-2],
                                                        zHI=self.options.xtpl_basis_sets[1][-3],
                                                        valueHI=results[-3])
            scf_energy = driver_cbs.scf_xtpl_helgaker_3("energies",
                                                        zLO=self.options.xtpl_basis_sets[1][-1],
                                                        valueLO=energies[-1],
                                                        zMD=self.options.xtpl_basis_sets[1][-2],
                                                        valueMD=energies[-2],
                                                        zHI=self.options.xtpl_basis_sets[1][-3],
                                                        valueHI=energies[-3])
        elif len(results) == 4:
            scf_result = driver_cbs.scf_xtpl_helgaker_2(f"{self.job_type}",
                                                        zLO=self.options.xtpl_basis_sets[1][-1],
                                                        valueLO=results[-1],
                                                        zHI=self.options.xtpl_basis_sets[1][-2],
                                                        valueHI=results[-2])
            scf_energy = driver_cbs.scf_xtpl_helgaker_2("eneriges",
                                                        zLO=self.options.xtpl_basis_sets[1][-1],
                                                        valueLO=energies[-1],
                                                        zHI=self.options.xtpl_basis_sets[1][-2],
                                                        valueHI=energies[-2])
        else:  # len(self.results) == 3:
            scf_result = driver_cbs.xtpl_highest_1(f"{self.job_type}",
                                                   zHI=self.options.xtpl_basis_sets[1][-1],
                                                   valueHI=results[-1])

            scf_energy = driver_cbs.xtpl_highest_1("eneriges",
                                                   zHI=self.options.xtpl_basis_sets[1][-1],
                                                   valueHI=energies[-1])

        self.result = corr_result.np + scf_result.np
        self.energy = corr_energy + scf_energy

        return self.result


class Delta(Procedure):

    def __init__(self, job_type, molecule, procedure_options, path="./HESS", iteration=0):
        self.delta_option_list = [procedure_options.delta_regexes,
                                  procedure_options.delta_templates,
                                  procedure_options.delta_dertypes,
                                  procedure_options.delta_programs,
                                  procedure_options.delta_parallels,
                                  procedure_options.delta_queues,
                                  procedure_options.delta_names,
                                  procedure_options.delta_scratches,
                                  procedure_options.delta_nslots,
                                  procedure_options.delta_time_limits]
        super().__init__(job_type, molecule, procedure_options, path, iteration)

    def flatten_procedure_options(self):
        flat_delta_list = [''] * len(self.delta_option_list)

        for delta_itr, delta_item in enumerate(self.delta_option_list):
            flat_delta_list[delta_itr] = [calc_option for delta_set in delta_item for calc_option
                                          in delta_set]
        return flat_delta_list

    @staticmethod
    def calculate_corrections(self):
        pass

    def compute_result(self):

        results = self.reap()
        energies = self.get_energies()

        result_corrections = []
        energy_corrections = []

        for itr in range(0, len(results), 2):
            result_corrections.append(results[itr] - results[itr + 1])
            energy_corrections.append(energies[itr] - energies[itr + 1])

        result_corrections = np.asarray(result_corrections)

        self.result = np.sum(result_corrections).tolist()
        self.energy = sum(energy_corrections)

        return self.result


class XtplDelta(Calculation):

    def __init__(self, job_type, molecule, procedure_options, path="./HESS", iteration=0):
        super().__init__(molecule, procedure_options, path)

        self.xtpl_procedure = Xtpl(job_type, molecule, procedure_options, path, iteration)
        self.delta_procedure = Delta(job_type, molecule, procedure_options, path, iteration)

        self.result = None
        self.energy = None

    def run(self):
        self.xtpl_procedure.run()
        self.delta_procedure.run()

    def compute_result(self):

        xtpl_result = self.xtpl_procedure.compute_result()
        xtpl_energy = self.xtpl_procedure.energy

        delta_result = self.delta_procedure.compute_result()
        delta_energy = self.delta_procedure.energy

        self.result = xtpl_result + delta_result
        self.energy = xtpl_energy + delta_energy

        return self.result


def xtpl_delta_wrapper(job_type, molecule, options, path='./HESS', iteration=0):
    if options.xtpl and options.options.delta:
        return True, XtplDelta(job_type, molecule, options, path, iteration)
    elif options.xtpl:
        return True, Xtpl(job_type, molecule, options, path, iteration)
    elif options.delta:
        return True, Delta(job_type, molecule, options, path, iteration)
    else:
        return False, None
