import copy
from abc import abstractmethod

import numpy as np
import psi4

from .template import TemplateFileProcessor
from .findifcalcs import FiniteDifferenceCalc, Gradient, Hessian
from .calculations import AnalyticCalc, Calculation, AnalyticGradient, AnalyticHessian


class Procedure(Calculation):
    """ A Procedure may be thought of as a list of Calculations with a matching list of instructions 'SOW'
    and 'REAP' to enable calculating a series of unique Calculations. 

    Creates AnalyticGradient, AnalyticHessian, Gradient (Finite Difference), and Hessian (Finite Difference) Calculation
    objects and runs them in parallel run. 

    This is a really just a framework for the Xtpl and Delta classes below. Would need to be generalized to implement
    new Procedures.

    """

    def __init__(self, job_type, molecule, procedure_options, path="./HESS", iteration=0):

        super().__init__(molecule, procedure_options, path)

        self.job_type = job_type
        self.iteration = iteration
        self.procedure_options = None # This will get set by the child class constructors

        self.energy = None
        self.result = None
        self.procedure = None
        self.calc_objects = None

    def _create_calc_objects(self):
        """ Use all the options for the procedures many calculations and Procedure attributes to
        create all the needed Calculation objects for a series of Calculations """

        calc_objects = []

        for calc_itr in range(len(self.procedure)):

            options = copy.deepcopy(self.options)
            calc_options = [proc_option[calc_itr] for proc_option in self.procedure_options]
            
            options.energy_regex = calc_options[0]
            options.template_file_path = calc_options[1]
            options.dertype = calc_options[2]
            options.program = calc_options[3]
            options.parallel = calc_options[4]
            options.queue = calc_options[5]
            options.name = calc_options[6]
            options.scratch = calc_options[7]
            options.nslots = calc_options[8]
            options.memory = calc_options[9]
            options.time_limit = calc_options[10]
            options.deriv_regex = calc_options[11]
            options.deriv_file = calc_options[12]

            print(options.deriv_file)
            print(calc_options[12])
            
            print(options.deriv_regex)
            print(options.dertype)

            if self.job_type == 'GRADIENT':
                calc_path = f"{self.path}/STEP{self.iteration:>02d}/{options.name}"
            else:
                calc_path = f"{self.path}/{options.name}"

            options.name = f"{options.name}--{self.iteration:>02d}"

            input_file = self.proc_inputs[calc_itr]
            print(calc_path)

            if self.job_type == 'HESSIAN':
                if options.dertype == 'HESSIAN':
                    calc_objects.append(AnalyticHessian(self.molecule,
                                                        input_file, 
                                                        options,
                                                        path=calc_path))
                elif options.dertype in ['ENERGY', 'GRADIENT']:
                    # Hessian will make decision within the class how to compute itself
                    calc_objects.append(Hessian(self.molecule, input_file, options, calc_path))
            else:
                # for optimization decide now how to compute the gradient
                if options.dertype == 'GRADIENT':
                    calc_objects.append(AnalyticGradient(self.molecule, 
                                                         input_file, 
                                                         options, 
                                                         path=calc_path))
                else:
                    calc_objects.append(Gradient(self.molecule, input_file, options, path=calc_path))

        return calc_objects

    def _create_input_files(self):
        """ Create list of InputFile objects for each calculation from templates
        Returns
        -------
        List[template.InputFile]

        """

        templates = self.procedure_options[1]
        template_strings = [open(template).read() for template in templates]
        xtpl_inputs = [TemplateFileProcessor(template, self.options).input_file_object for template in
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

    def unique_calculations(self):
        unique = []
        for calc_itr, calc in enumerate(self.calc_objects):
            if self.procedure[calc_itr] == 'SOW':
                if isinstance(calc, AnalyticCalc) or isinstance(calc, FiniteDifferenceCalc):
                    unique.append(calc)
                else:
                    raise ValueError("Procedure cannot run calculations that aren't of type AnalyticCalc or FindifCalc")
        return unique

    def write_input(self, backup=False):
        for calc in self.unique_calculations():
            calc.write_input()

    def run(self):
        return [calc.run() for calc in self.unique_calculations()]

    def reap(self, force_resub=False):
        return [calc.reap(force_resub) for calc in self.calc_objects]

    def get_energies(self):
        return [calc.get_reference_energy() for calc in self.calc_objects]

    def get_reference_energy(self):
        """ Called reference to match findif method name reference in terms of displacements """
        return self.energy

    def get_result(self, force_resub=False):
        return [calc.get_result(force_resub) for calc in self.calc_objects]

class Xtpl(Procedure):
    """ A child class of Procedure. 

    Represents a basis set extrapolation of gradients or hessians. This creates
    the Calculation objects needed to perform each individual calculation.

    Attributes
    ----------
    self.xtpl_option_list : list
        all xtpl_<option> options. These will be used to create more specific Options objects
        for the individual calculations


    Methods
    -------

    get_result(force_resub=False)
        collects all gradients or hessians in self.calculations and performs the basis set
        extrapolation as described by Options.xtpl_basis_sets and Options.xtpl_scf.
        Always performs a two point correlation energy extrapolation and can be either
        2 point, 3 point or largest (additive) basis set extrapolation.
    
    """
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
                                 procedure_options.xtpl_time_limits,
                                 procedure_options.xtpl_deriv_regexes,
                                 procedure_options.xtpl_deriv_files,
                                 procedure_options.xtpl_basis_sets]
        super().__init__(job_type, molecule, procedure_options, path, iteration)

        self.procedure_options = self.flatten_procedure_options()
        self.proc_inputs = self._create_input_files()
        self.procedure = self._reap_sow_ordering()
        self.calc_objects = self._create_calc_objects()

    def flatten_procedure_options(self):
        return [xtpl_option[0] + xtpl_option[1] for xtpl_option in self.xtpl_option_list]

    def get_reference_energy(self):
        return self.energy
    
    def get_result(self, force_resub=False):
        

        # CLARIFICATION. optavc reads in extrapolation input in the order large to small
        # this is a hold over from a previous version where that actually made sense
        # psi4 specifies basis sets in the order small to large. Indices may be flipped
        # from what you would expect therefore

        results = list(map(psi4.core.Matrix.from_array, super().get_result(force_resub)))
        energies = self.get_energies()


        corr_result = psi4.driver.driver_cbs.corl_xtpl_helgaker_2(f"{self.job_type}",
                                                      zLO=self.options.xtpl_basis_sets[0][1],
                                                      valueLO=results[1],
                                                      zHI=self.options.xtpl_basis_sets[0][0],
                                                      valueHI=results[0])
        corr_energy = psi4.driver.driver_cbs.corl_xtpl_helgaker_2("energies",
                                                      zLO=self.options.xtpl_basis_sets[0][1],
                                                      valueLO=energies[1],
                                                      zHI=self.options.xtpl_basis_sets[0][0],
                                                      valueHI=energies[0])

        # indexes using 2 and 3 instead of -x like in below if statements since we could perform
        # a dz, tz, qz scf but only need the qz and tz in compensating for extrapolating the
        # reference energy with the correlation energy
        scf_result_corr = psi4.driver.driver_cbs.corl_xtpl_helgaker_2(f"scf correlated {self.job_type}",
                                                      zLO=self.options.xtpl_basis_sets[0][1],
                                                      valueLO=results[3],
                                                      zHI=self.options.xtpl_basis_sets[0][0],
                                                      valueHI=results[2])
        scf_energy_corr = psi4.driver.driver_cbs.corl_xtpl_helgaker_2("scf correlated energies",
                                                      zLO=self.options.xtpl_basis_sets[0][1],
                                                      valueLO=energies[3],
                                                      zHI=self.options.xtpl_basis_sets[0][0],
                                                      valueHI=energies[2])

        # do the correction for extrapolating with the total energy
        corr_result = corr_result.np - scf_result_corr.np
        corr_energy = corr_energy - scf_energy_corr

        

        # now perform the extrapolation of the reference energy 
        if self.options.scf_xtpl:
        
            if len(self.procedure_options[-1]) == 5:
                scf_result = psi4.driver.driver_cbs.scf_xtpl_helgaker_3(f"{self.job_type}",
                                                            zLO=self.options.xtpl_basis_sets[1][-1],
                                                            valueLO=results[-1],
                                                            zMD=self.options.xtpl_basis_sets[1][-2],
                                                            valueMD=results[-2],
                                                            zHI=self.options.xtpl_basis_sets[1][-3],
                                                            valueHI=results[-3])
                scf_energy = psi4.driver.driver_cbs.scf_xtpl_helgaker_3("energies",
                                                            zLO=self.options.xtpl_basis_sets[1][-1],
                                                            valueLO=energies[-1],
                                                            zMD=self.options.xtpl_basis_sets[1][-2],
                                                            valueMD=energies[-2],
                                                            zHI=self.options.xtpl_basis_sets[1][-3],
                                                            valueHI=energies[-3])
            elif len(self.procedure_options[-1]) == 4:
                scf_result = psi4.driver.driver_cbs.scf_xtpl_helgaker_2(f"{self.job_type}",
                                                            zLO=self.options.xtpl_basis_sets[1][-1],
                                                            valueLO=results[-1],
                                                            zHI=self.options.xtpl_basis_sets[1][-2],
                                                            valueHI=results[-2])
                scf_energy = psi4.driver.driver_cbs.scf_xtpl_helgaker_2("eneriges",
                                                            zLO=self.options.xtpl_basis_sets[1][-1],
                                                            valueLO=energies[-1],
                                                            zHI=self.options.xtpl_basis_sets[1][-2],
                                                            valueHI=energies[-2])
        else:
            # don't extrapolate add to largest scf
            scf_result = psi4.driver.driver_cbs.xtpl_highest_1(f"{self.job_type}",
                                                   zHI=self.options.xtpl_basis_sets[1][-2],
                                                   valueHI=results[-2])

            scf_energy = psi4.driver.driver_cbs.xtpl_highest_1("eneriges",
                                                   zHI=self.options.xtpl_basis_sets[1][-2],
                                                   valueHI=energies[-2])

        # corr_result is already converted from psi4 matrix to numpy array
        self.result = corr_result + scf_result.np
        self.energy = corr_energy + scf_energy

        print("\n\nExtrapolation procedure has finished")
        print(f"The result for extrapolation procedure is:\n{self.result}")
        print(f"The energy from the extrapolation procedure is:\n{self.energy}")
       
        return self.result

class Delta(Procedure):
    """ Child class of Procedure to represent performing an arbitrary number of additive corrections
    to gradients and hessians.

    This class is not really meant to be a called without Xtpl. Please use XtplDelta.

    Attributes
    ----------
    self.delta_options_list : List
        All of the delta_<option> options in the standard format of a list of two dimensional corrections.
        These options will be used to create a series of Options objects by setting the corresponding
        standard options with the delta options entries.

        Assumes the Options object contins only properly formatted options.
    
    Methods
    -------
    self.return_result

        Takes a simple difference between the first item in a two dimensional correction and the second. All corrections
        are then summed together and the sum is taken as the result


    """


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
                                  procedure_options.delta_memories,
                                  procedure_options.delta_time_limits,
                                  procedure_options.delta_deriv_regexes,
                                  procedure_options.delta_deriv_files]

        super().__init__(job_type, molecule, procedure_options, path, iteration)

        self.procedure_options = self.flatten_procedure_options()
        self.proc_inputs = self._create_input_files()
        self.procedure = self._reap_sow_ordering()
        self.calc_objects = self._create_calc_objects()
    
    def flatten_procedure_options(self):
        flat_delta_list = [''] * len(self.delta_option_list)

        for delta_itr, delta_item in enumerate(self.delta_option_list):
            flat_delta_list[delta_itr] = [calc_option for delta_set in delta_item for calc_option
                                          in delta_set]
            print(flat_delta_list[delta_itr])
        return flat_delta_list

    @staticmethod
    def calculate_corrections(self):
        pass

    def get_result(self, force_resub=False):
        
        results = super().get_result(force_resub)
        energies = super().get_energies()

        result_corrections = []
        energy_corrections = []

        for itr in range(0, len(results), 2): 
            result_corrections.append(results[itr] - results[itr + 1]) 
            energy_corrections.append(energies[itr] - energies[itr + 1]) 

        result_corrections = np.asarray(result_corrections)

        # add all arrays elementwise
        self.result = np.sum(result_corrections, axis=0)
        self.energy = sum(energy_corrections)

        print("\n\nCorrection procedure has finished")
        print(f"The result for the correction procedure is:\n{self.result}")
        print(f"The energy from the correction procedure is:\n{self.energy}")
        return self.result
        

class XtplDelta(Procedure):
    """ A Procedure written to run the Xtpl and Delta Procedures in parallel. Creates the Xtpl and Delta
    
    Seqentially calls write_input, run, and get_result for the Xtpl and Delta procedures. Adds the results from
    Xtpl and Delta together.

    #TODO this should be rewritten to utlilize the _reap_sow_ordering and unique_calculations methods in the
    base class to eliminiate redundant calculations between the Xtpl and Delta classes

    """

    def __init__(self, job_type, molecule, procedure_options, path="./HESS", iteration=0):
        super().__init__(job_type, molecule, procedure_options, path)

        self.xtpl_procedure = Xtpl(job_type, molecule, procedure_options, path, iteration)
        self.delta_procedure = Delta(job_type, molecule, procedure_options, path, iteration)

        self.result = None
        self.energy = None
        self.calc_objects = self.xtpl_procedure.calc_objects + self.delta_procedure.calc_objects

    def run(self):
        self.xtpl_procedure.run()
        self.delta_procedure.run()

    def write_input(self, backup=False):
        self.xtpl_procedure.write_input()
        self.delta_procedure.write_input()

    def get_result(self, force_resub=False):

        xtpl_result = self.xtpl_procedure.get_result(force_resub=False)
        xtpl_energy = self.xtpl_procedure.get_reference_energy()
        
        delta_result = self.delta_procedure.get_result(force_resub=False)
        delta_energy = self.delta_procedure.get_reference_energy()

        self.result = xtpl_result + delta_result
        self.energy = xtpl_energy + delta_energy
        
        print("\n\n\n*** ============================================= ***")
        print("Extrapolation and Correction procedures have finished: ")
        print(f"The final result is:\n{self.result}")
        print(f"The final energy is:\n{self.energy}")
        print("*** ============================================= ***")
       
        return self.result

def xtpl_delta_wrapper(job_type, molecule, options, path='./HESS', iteration=0):
    if options.xtpl and options.delta:
        return True, XtplDelta(job_type, molecule, options, path, iteration)
    elif options.xtpl:
        return True, Xtpl(job_type, molecule, options, path, iteration)
    elif options.delta:
        raise NotImplementedError("Can't just perform a correction."
                                  "You probably want to perform an XtplDelta calculation if you're "
                                  "looking to use the Delta functionality.")
        return True, Delta(job_type, molecule, options, path, iteration)
    else:
        return False, None

