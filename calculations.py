import os
import subprocess
import re
import shutil
import copy
import time
import hashlib
from abc import ABC, abstractmethod

import numpy as np
from psi4.core import Matrix
from psi4.driver.qcdb import cfour, hessparse 

from .cluster import Cluster
from .template import TemplateFileProcessor

class Calculation(ABC):
    """ This is the Base class for everything calculation related in optavc. Its purpose is really to define
    the API for the write_input, run, get_result, and compute_result methods.

    The basic Hierarchy of Calculation is:

    Optimizations can contain one or more Procedure, FiniteDifferenceCalc, or AnalyticCalc (only 1 at a time)

    Procedures can contain one or more FiniteDifferenceCalc or AnalyticCalc.

    FiniteDifferenceCalc can itself contain one or more AnalyticCalc (always of the same kind)


    In this hierarchy any Calculation that consists of other Calculations lower in the hierarchy is able
    to run all Calculations in parallel through the write_inputs, run, and get_result methods.
    Calling compute_result repetively will result in non parallel executation of the sub calculations.

    Attributes
    ----------
    molecule : molecule.Molecule
        optavc's custom very basic molecule class that can be interconverted to psi4's molecule
    options : opions.Object
        At every level of the Calculation Hierarchy this will become a copy of the higher levels
        options with (potentially) modifications made by the higher level Calculation.
    path : str
        path-like representation of the directory where the Calculation itself will be run
        changes throughout the Calculation hierarchy

    Methods
    -------
    write_input()
        write ALL input files for the Calculation class.

    run()
        run ALL input files contained in the Calculation class. A simple submission of all jobs (at once)
        to the cluster.

    get_result()
        get ALL results for the Calculation class.

self.reap    compute_result()
        calls write_input, run, and get_result all together. This requires a waiting period between running the
        calculations and getting the results of course.

    """


    def __init__(self, molecule, options, path=".", key=None):
        self.molecule = molecule
        self.options = copy.deepcopy(options)
        self.path = os.path.abspath(path)
        self.key = key
        self.dict_obj = {}

    def __str__(self):

        return f"{self.class_name()}: {self.options.name}"

    def __repr__(self):

        return f"{self.class_name()}: {self.options.name}"

    def class_name(self):
        """ return AnalyticGradient from <class 'optavc.calculations.AnalyticGradient'> """
        tmp = str(self.__class__)
        tmp = tmp.split("'")
        return tmp[-2].split(".")[-1]

    def to_dict(self):
        """ Not generally used. Serialize all object attributes and add in subset of keywords """
        self.dict_obj = self.__dict__
        self.dict_obj['type'] = self.__class__.__name__
        self.dict_obj['path'] = self.path
        self.dict_obj['options'] = {}
        # for i in self.options:
        if self.options.mpi is not None:
            self.dict_obj['options']['command'] = self.options.command
        # self.dict['options']['prep_cmd'] = self.options.prep_cmd
        self.dict_obj['options']['output_name'] = self.options.output_name
        self.dict_obj['options']['energy_regex'] = self.options.energy_regex
        self.dict_obj['options'][
            'correction_regexes'] = self.options.correction_regexes
        self.dict_obj['options']['success_regex'] = self.options.success_regex
        self.dict_obj['options']['fail_regex'] = self.options.fail_regex
        self.dict_obj['path'] = self.path
        return self.dict_obj

    @abstractmethod
    def run(self):
        """Standalone method. Implementations for child classes should simply move to the
        correct directory and execture the submission script. Enables higher level classes
        to run AnalyticCalculation classes in parallel

        :meta private:

        Returns
        -------
        Union[str, list[str]]: output from submission or list of outputs from submissions

        """
        pass

    @abstractmethod
    def get_result(self, force_resub=False, skip_wait=False):
        """getter for the final result of a Calculation. Run or compute_result must already have
        been executed

        :meta private:

        """
        pass

    @abstractmethod
    def write_input(self, backup=False):
        pass

    def compute_result(self):
        """Wrapper method to run a calculation from scratch. Write inputs. Run calculations.
        Collect results for any and all Calculations
        AnalyticCalc and FindifCalc reimplement this with better ways to wait. The Procedure class
        does simply inherit this.
        :meta private:
        """
        self.write_input()
        self.run()
        time.sleep(40)
        return self.get_result()


class AnalyticCalc(Calculation):
    """Parent class for the three real types of calculations that can be run. All other child classes will have one or
    more instances of AnalyticCalc or instances of classes that have instances of AnalyticCalc.

    This class contains the necessary code to perform the actual execution of Gradients, Singlepoints, and Hessians.
    For result collection please see AnalyticGradient and Singlepoint child classes

    Still cannot be instantiated: the abstract method get_result is not implemented here.

    Attributes
    ----------
    self.cluster : cluster.Cluster
        a class that manages how a Calculation is able to interact with the Cluster queueing a submission
        system
    self.resub_count : int
        keeps track of whether we have exceed Options.resub_max for each Calculation

    Methods
    -------
    run()
        This is the base implementation of run. calls cluster.submit or tries to execute the program
        on the host in a somewhat standard fashion (not guarranteed to work). The working directory
        must be changed to where the input has been written (the path of the Calculation) and then
        returns to the directory of the Parent Calculation. Returns the job_id (or zero) if no cluster id
        Parent implemenations generally just call this method for each of their Calculation objects.

    write_input()
        This is the base implementation of write_input. Updates the input file object with
        this calculations molecule information, then writes it to the location given to this
        calculation by its Parent Calculation. Copy any other files needed.
        Parent implemenations generally just call this method for each of their Calculation objects.

    wait_for_calculation()
        uses Options.sleepy_sleep_time to hold until this specific calculation is finished

    """

    def __init__(self, molecule, inp_file_obj, options, path=".", key=None):
        super().__init__(molecule, options, path, key)
        self.inp_file_obj = inp_file_obj
        self.options.job_array = False  # If interacting with singlepoint, cannot use array or -sync
        self.options.job_array_range = (1, 1)  # job array range always checked in submitter

        self.file_not_found_behavior = None
        self.disp_num = None

        if self.options.cluster == 'HOST':
            self.cluster = None
        else:
            self.cluster = Cluster(self.options.cluster)

        self.resub_count = 0
        self.job_num = None

    def run(self):
        """ Change to singlepoint directory. Effect is to invoke subprocess

        :meta private:

        Returns
        -------
        str : output captured from qsub <name>.sh """

        working_directory = os.getcwd()
        os.chdir(self.path)

        if self.options.cluster ==  'HOST':
            pipe = subprocess.PIPE
            process = subprocess.run([f'{self.options.program}',
                                      f'{self.options.input_name}',
                                      '-o',
                                      f'{self.options.output_name}'],
                                     stdout=pipe, stderr=pipe, encoding='UTF-8')
            if process.stderr:
                print(process.stderr)
                raise RuntimeError("Error while running on host")
            output = 0  # don't need to return job_id
        else:
            output = self.cluster.submit(self.options)
            self.job_num = output
        os.chdir(working_directory)
        self.job_num = output
        return output

    def write_input(self, backup=False):
        """ Uses template.InputFile.make_input() to replace the geometry in
        the user provided template file. Writes input file to the calculations
        directory

        :meta private:

        """

        if not os.path.exists(self.path):
            os.makedirs(self.path)
        self.molecule.set_units(self.options.input_units)

        if backup:
            backup_template_str = open(self.options.backup_template).read()
            tfp = TemplateFileProcessor(backup_template_str, self.options).input_file_object
            input_text = tfp.make_input(self.molecule.geom)
        else:
            input_text = self.inp_file_obj.make_input(self.molecule.geom)

        input_path = os.path.join(self.path, self.options.input_name)
        input_file = open(input_path, 'w')
        input_file.write(input_text)
        for file_name in self.options.files_to_copy:
            shutil.copy(file_name, self.path)

    def check_status(self, status_str, return_text=False):
        """ Check for status_str within a output_file. This is how optavc finds failed jobs. 
        This information is necessary but not sufficient to resubmit a job on sapelo (job_state
        must also be confirmed via queuing system)

        Parameters
        ----------
        status_str : str
            generally options.success_regex or options.fail_regex

        Returns
        -------
        bool : True if the string was found.
            Read if check_status(status_string): statements with care
        output_text : str
            if requested            

        Raises
        ------
        FileNotFoundError

        Notes
        -----
        method should called through get_energy_from_output in standard workflow

        """

        output_path = os.path.join(self.path, self.options.output_name)
        try:
            with open(output_path) as f:
                output_text = f.read()
        except FileNotFoundError:
            if not self.options.resub:
                print(self.file_not_found_behavior)
                print(f"Tried to open {output_path}")
            raise
        else:
            check = re.search(r'^' + status_str, output_text, re.MULTILINE)
            if return_text:
                return check, output_text
            return check

    def wait_for_calculation(self):
 
        wait = True
        while wait:
            try:
                finished, job_num = self.cluster.query_cluster(self.job_num, self.options.job_array)
            except RuntimeError:
                time.sleep(10)
                finished, job_num = self.cluster.query_cluster(self.job_num, self.options.job_array)

            if finished:
                status = self.check_status(self.options.energy_regex)
                wait = False
            else:
                time.sleep(self.cluster.resub_delay(self.options.sleepy_sleep_time))

        return finished, job_num

    def compute_result(self):
        self.write_input()
        self.run()
        time.sleep(self.cluster.wait_time)
        self.wait_for_calculation()
        return self.get_result()

    def _get_energy_float(self, regex_str, output_text):
        try:
            return float(re.findall(regex_str, output_text)[-1])
        except (ValueError, IndexError) as e:
            if regex_str == '':
                return 0.0
                # Yes, yes, I'm silencing an exception no one cares. regex_str can be '' in the
                # case of no correction being included
            else:
                raise ValueError(f"Could not find energy for singlepoint {self.disp_num} using "
                                 f" {regex_str}")

class SinglePoint(AnalyticCalc):
    """ Handles lookup of the result for a Singlepoint. Extends AnalyticCalculation by adding the get_result
    behavior for a Singlepoint.

    Attributes
    ----------
    self.disp_num : int

    Methods
    -------
    get_result()
        get the energy (with a correction if needed) from an output file.

    """

    def __init__(self, molecule, inp_file_obj, options, path=".", disp_num=1, key=None):
        super().__init__(molecule, inp_file_obj, options, path, key)
        self.disp_num = disp_num
        self.file_not_found_behavior = f"Could not open output file for singlepoint: {self.disp_num}"

    def get_result(self):
        """ Use regex module to find and return energy with any necessary corrections

        :meta private:

        """

        if not self.check_status(self.options.energy_regex):
            return None
            # raise RuntimeError(f"Calculation {name} finished but could not get result using"
            #                    f"regex: {self.options.energy_regex}")

        output_path = os.path.join(self.path, self.options.output_name)

        with open(output_path) as f:
            output = f.read()

        energy = self._get_energy_float(self.options.energy_regex, output)
        correction = sum(self._get_energy_float(correction_regex, output)
                         for correction_regex in self.options.correction_regexes)
        # If no correction, adding zero. Add to correlation energy if 2 energies
        return energy + correction

class AnalyticGradient(AnalyticCalc):
    """ This class was implemented in order to use CFour's analytic gradients with the psi4 CBS
    procedure. CCSD(T) gradients from CFour are not available through the Psi4/CFour interface.

    Uses psi4.qcdb to rotate / align the gradient and molecule back into optavc's molecular
    orientation if using cfour gradients.

    Methods
    -------
    get_result()
        This is the first class in the hierarchy that is really meant to just be run without management by
        a Parent class. Therefore if the calculation is not finished, optavc will check the queue for this
        job at intervals. returns a numpy array

    get_reference_energy()
        All classes at a higher level than this in the hierarchy will now need the energy seperate from the
        result

    """

    def __init__(self, molecule, inp_file_obj, options, disp_num=None, path=".", key=None):
        super().__init__(molecule, inp_file_obj, options, path, key)

        not_found = "Gradient calculation has failed."

        if disp_num:
            self.file_not_found_behavior = f"{not_found} for displacement {disp_num}"
        else:
            self.file_not_found_behavior = not_found

        self.disp_num = disp_num

    # def reap(self, force_resub):
    #     """ force_resub is only here to match interface for findifcalc resub
    #     reap is only called from optimization when gradient is expected to
    #     have already finished """

    #     return self.get_result(skip_wait=False)

    def get_result(self, force_resub=False):
        """ Gets the gradient according to method specified by user

        :meta private:

        Returns
        -------
        np.ndarray
            shape: (natom, 3)

        """

        if force_resub:
            if not self.check_status(self.options.energy_regex):
                self.run()

        # if self.job_num is None run has not been called. Either this is by mistake or we're performing a restart
        if self.job_num:
            self.wait_for_calculation()

        if not self.check_status(self.options.energy_regex):
            raise RuntimeError(f"Calculation {self.options.name} finished but could not get result using"
                               f"regex: {self.options.energy_regex}")

        if self.options.deriv_file == 'output':
            try:
                return self.grad_from_output()
            except AttributeError as e:
                # capture attribute error from accessing NoneType
                raise RuntimeError("Energy check successful but could not find gradient in output file for calc"
                                   f"{self.options.name}. Check output file: {self.path}") from e
        else:
            return self.grad_file_lookup()

    def grad_from_output(self):
        output_path = os.path.join(self.path, self.options.output_name)
        with open(output_path) as f:
            output = f.read()

        # add gradient regex to header regex supplied by user.
        label_xyz = r"(\s*.*(\s*-?\d+\.\d+){3})+"
        regex = self.options.deriv_regex + label_xyz
        grad_str = re.search(regex, output).group()

        # cleaned_array = np.where(np.abs(gradient_array) > 1e-14, gradient_array, 0.0)

        # aligned_grad = self.rotate_matrix(output, cleaned_array) 
        # return np.where(np.abs(aligned_grad) > 1e-14, aligned_grad, 0.0)

        gradient_array = self.str_to_ndarray(grad_str)
        return gradient_array

    def get_reference_energy(self):
        """ Get reference energy from gradient calculation

        :meta private:

        Returns
        -------
        float

        """

        output_path = os.path.join(self.path, self.options.output_name)

        with open(output_path) as f:
            output = f.read()

        return self._get_energy_float(self.options.energy_regex, output)

    def grad_file_lookup(self):

        file_path = os.path.join(self.path, self.options.deriv_file)

        with open(file_path, 'r') as f:
            grad_file = f.read()

        if self.options.program.lower() == 'cfour':
            import qcelemental as qcel

            molecule, cfour_grad = cfour.harvest_GRD(grad_file)
            cfour_mol, _, _, _, c4_unique = molecule.to_arrays()

            psi_mol, _, _, _, psi_unique = self.molecule.cast_to_psi4_molecule_object().to_arrays()

            print("rotating molecule and gradient with qcelemental align")
            rmsd, qcel_alignment_mill = qcel.molutil.align.B787(rgeom=psi_mol,
                                                                cgeom=cfour_mol,
                                                                runiq=psi_unique,
                                                                cuniq=c4_unique,
                                                                verbose=0)
            gradient = qcel_alignment_mill.align_gradient(np.asarray(cfour_grad))
        else:
            gradient = self.str_to_ndarray(grad_file)

        return gradient

    def str_to_ndarray(self, grad_output):
        """ Take string with possible header from the output file or a specified gradient file
        and convert to psi4 matrix

        Notes
        -----
        ignores any header grabs the last three columns of the last 'natom' lines and converts to
        a psi4 matrix via numpy array """

        grad_lines = grad_output.split("\n")
        # drop labels if present (assumes labels in first whitespace separated column) for
        # last lines in string. Assumes dE/dx, ... values are the last lines in string
        twoD_grad_str = [line.split()[-3:] for line in grad_lines[-self.molecule.natom:]]
        twoD_grad = np.asarray(twoD_grad_str).astype(float)
        return twoD_grad

class AnalyticHessian(AnalyticCalc):
    """ This class was implemented in order to use CFour's analytic hessians with the psi4 CBS

    This class performs the same functionality as AnalyticGradient. See docs.

    """

    def __init__(self, molecule, inp_file_obj, options, disp_num=None, path=".", key=None):
        super().__init__(molecule, inp_file_obj, options, path, key)

        not_found = "Hessian calculation has failed."

    # def reap(self, force_resub):
    #     """ force_resub is only here to match interface for findifcalc resub
    #     reap is only called from optimization when gradient is expected to
    #     have already finished """

    #     return self.get_result(skip_wait=False)

    def get_result(self, force_resub=False):
        """ Gets the hessian according to method specified by user

        :meta private:

        Returns
        -------
        np.ndarray
            shape: (natom, 3)

        """

        if force_resub:
            if not self.check_status(self.options.energy_regex):
                self.run()

        if self.job_num:
            self.wait_for_calculation()

        if not self.check_status(self.options.energy_regex):
            raise RuntimeError(f"Calculation {self.options.name} finished but could not get result using"
                               f"regex: {self.options.energy_regex}")

        if self.options.deriv_file == 'output':
            try:
                hessian_array = self.output_file_lookup()
            except AttributeError as e:
                # capture attribute error from calling .group on NoneType returned from re.search
                raise RuntimeError("Energy check was successful but could not find the Hessian in the otuput file for"
                                   f"{self.options.name}. Check output file {self.path}") from e
        else:
            hessian_array = self.hessian_file_lookup()

        return hessian_array

    def hessian_file_lookup(self):
        """Try to get the hesian from a special written file. Assuming a naive format.

        Use psi4 qcdb machinery to get a hessian from cfour and ensure proper orientation """

        file_path = os.path.join(self.path, self.options.deriv_file)

        with open(file_path) as f:
            hess_string = f.read()

        if self.options.program.lower() == 'cfour':

            hessian = hessparse.load_hessian(hess_string, dtype="fcmfinal")
            return self.rotate_hessian(hessian)

        hess_rows = hess_string.split("\n")[-3*self.molecule.natom:]
        hessian_list = [row.split() for row in hess_rows]

        return np.asarray(hess_rows).astype(float)

    def output_file_lookup(self):
        output_path = os.path.join(self.path, self.options.output_name)

        with open(output_path) as f:
            output = f.read()

        # add hessian regex to header regex supplied by user.
        label_xyz = r"(\s*.*(\s*-?\d+\.\d+){3})+"
        regex = self.options.result_regex + label_xyz
        grad_str = re.search(regex, output).group()

        return self.str_to_ndarray(grad_str)

    def rotate_hessian(self, hessian):
        """only needed for cfour. Same procedure as in psi4. Use grad file to rotate the internal molecular orientaiton
        back to the psi4 (user) orientation. Then rotate the hessian """

        import qcelemental as qcel

        file_path = os.path.join(self.path, 'GRD')
        with open(file_path, 'r') as f:
            grad_file = f.read()


        molecule, cfour_grad = cfour.harvest_GRD(grad_file)
        cfour_mol, _, _, _, c4_unique = molecule.to_arrays()

        psi_mol, _, _, _, psi_unique = self.molecule.cast_to_psi4_molecule_object().to_arrays()

        print("rotating molecule and gradient with qcelemental align")
        rmsd, qcel_alignment_mill = qcel.molutil.align.B787(rgeom=psi_mol,
                                                            cgeom=cfour_mol,
                                                            runiq=psi_unique,
                                                            cuniq=c4_unique,
                                                            verbose=0)
        return qcel_alignment_mill.align_hessian(hessian)

    def get_reference_energy(self):
        """ Get reference energy from gradient calculation

        Returns
        -------
        float

        """

        output_path = os.path.join(self.path, self.options.output_name)

        with open(output_path) as f:
            output = f.read()

        return self._get_energy_float(self.options.energy_regex, output)

    def str_to_ndarray(self, grad_output):
        """ Take string with possible header from the output file or a specified gradient file
        and convert to psi4 matrix

        Notes
        -----
        ignores any header grabs the last three columns of the last 'natom' lines and converts to
        a psi4 matrix via numpy array """

        grad_lines = grad_output.split("\n")
        # drop labels if present (assumes labels in first whitespace separated column) for
        # last lines in string. Assumes dE/dx, ... values are the last lines in string
        twoD_grad_str = [line.split()[-3:] for line in grad_lines[-self.molecule.natom:]]
        twoD_grad = np.asarray(twoD_grad_str).astype(float)
        return twoD_grad
