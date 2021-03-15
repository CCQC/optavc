""" 
Contains the basic calculation class from which a SinglePoint, FiniteDifferencecCalc and 
Optimization are derived.

Calculation
Consists of instances of the optavc molecule and inputfile and options classes
which has some run function.
Any time a new calculation class is created, a deepcopy of options is performed. 


Singlepoint
-----------

Since otpavc only performs finite differences by singlepoint, much of the machinery
lies here. Gradient, and Hessian loop through a list of SinglePoints for most of their
tasks

Controls writing template files, running individual singlepoints,  
"""


import os
import subprocess
import re
import shutil
import copy
import time
from abc import ABC, abstractmethod

import numpy as np
from psi4.core import Matrix

from .cluster import Cluster


class Calculation(ABC):
    def __init__(self, molecule, options, path=".", key=None):
        self.molecule = molecule
        self.options = copy.deepcopy(options)
        self.path = os.path.abspath(path)
        self.key = key
        self.dict_obj = {}
        self.resub_count = 0

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
        
        Returns
        -------
        Union[str, list[str]]: output from submission or list of outputs from submissions

        """
        pass

    @abstractmethod
    def get_result(self, force_resub=False, skip_wait=False):
        """getter for the final result of a Calculation. Run or compute_result must already have 
        been executed """
        pass

    @abstractmethod
    def write_input(self):
        pass

    def compute_result(self):
        """Wrapper method to run a calculation from scratch. Write inputs. Run calculations. 
        Collect results for any and all Calculations 
        AnalyticCalc and FindifCalc reimplement this with better ways to wait. The Procedure class
        does simply inherit this.
        """ 
        self.write_input()
        self.run()
        time.sleep(40)
        return self.get_result()


class AnalyticCalc(Calculation):
    """Parent class for the two real types of calculations that can be run. All other child classes will have one or
    more instances of AnalyticCalc. 
    
    This class contains the necessary code to perform the actual execution of Gradients and Singlepoints.
    For result collection please see AnalyticGradient and Singlepoint child classes

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

        self.job_num = None

    def run(self):
        """ Change to singlepoint directory. Effect is to invoke subprocess 
        Returns
        -------
        str : output captured from qsub *.sh """

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

        os.chdir(working_directory)
        self.job_num = output
        return output

    def write_input(self):
        """ Uses template.InputFile.make_input() to replace the geometry in
        the user provided template file. Writes input file to the calculations
        directory
        """

        if not os.path.exists(self.path):
            os.makedirs(self.path)
        self.molecule.set_units(self.options.input_units)
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
    """ Handles lookup of the result for a Singlepoint """

    
    def __init__(self, molecule, inp_file_obj, options, path=".", disp_num=1, key=None):
        super().__init__(molecule, inp_file_obj, options, path, key)
        self.disp_num = disp_num
        self.file_not_found_behavior = f"Could not open output file for singlepoint: {self.disp_num}"

    def get_result(self):
        """ Use regex module to find and return energy with any necessary corrections"""

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

    # These two functions are purely here for the testing of the resub functionality
    def check_resub(self):
        """ Check/test the resubmission feature. Searches for the 'Giraffe' inserted by
        'insert_Giraffe' function.
        Parameters
        ----------
        N/A
        Returns
        -------
        bool
        """
        output_path = os.path.join(self.path, self.options.output_name)
        output_text = open(output_path).read()
        return re.search('Giraffe', output_text)
    
    def insert_Giraffe(self):
        """ Inserts the string 'Giraffe' into all output files. Useful for testing regex
        dependent methods as a proof of concept.
        Parameters
        ----------
        N/A
        Returns
        -------
        N/A, all it does is insert 'Giraffe' into the output text. Trust me, it's useful.
        """
        output_path = os.path.join(self.path, self.options.output_name)
        output_text = open(output_path).read()
        output_text += 'Giraffe'
        with open(output_path, 'w') as file:
            file.writelines(output_text)


class AnalyticGradient(AnalyticCalc):
    """ This class was implemented in order to use CFour's analytic gradients with the psi4 CBS
    procedure. CCSD(T) gradients from CFour are not available through the Psi4/CFour interface.
    
    Handles the lookup of output from a Gradient calculation. Adds the ability to wait for a calculation
    to finish on the cluster before getting a result. 

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
 
        output_path = os.path.join(self.path, self.options.output_name)
        
        with open(output_path) as f:
            output = f.read()
    
        # add gradient regex to header regex supplied by user.
        label_xyz = r"(\s*.*(\s*-?\d+\.\d+){3})+"
        regex = self.options.deriv_regex + label_xyz
        grad_str = re.search(regex, output).group()
 
        return self.str_to_ndarray(grad_str)

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

class AnalyticHessian(AnalyticCalc):
    """ This class was implemented in order to use CFour's analytic hessians with the psi4 CBS
    
    Handles the lookup of output from a Hessian calculation. Adds the ability to wait for a calculation
    to finish on the cluster before getting a result. 

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
 
        if self.options.hessian_file == 'output':
            return self.output_file_lookup()
        else:
            return self.hessian_file_lookup()

    def hessian_file_lookup(self):
        
        with open(self.options.hessian_file) as f:
            hess_string = f.read()

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
