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
from abc import ABC, abstractmethod

import numpy as np
from psi4.core import Matrix

from .cluster import Cluster


class Calculation(ABC):
    def __init__(self, molecule, inp_file_obj, options, path=".", key=None):
        self.molecule = molecule
        self.inp_file_obj = inp_file_obj
        self.options = copy.deepcopy(options)
        self.path = os.path.abspath(path)
        self.key = key
        self.dict_obj = {}
        self.resub_count = 0
        if self.options.cluster == 'HOST':
            self.cluster = None
        else:
            self.cluster = Cluster(self.options.cluster)

    def to_dict(self):
        """ Not generally used. Serialize all object attributes and add in subset of keywords """
        self.dict_obj = __dict__
        self.dict_obj['type'] = self.__name__
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
        pass


class AnalyticCalc(Calculation):
    
    def __init__(self, molecule, inp_file_obj, options, path=".", key=None):
        super().__init__(molecule, inp_file_obj, options, path, key)
        self.options.job_array = False  # If interacting with singlepoint, cannot use array or -sync
        self.options.job_array_range = (1, 1)  # job array range always checked in submitter

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

    @abstractmethod
    def get_result(self):
        pass

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

    def __init__(self, molecule, inp_file_obj, options, path=".", disp_num=1, key=None):
        super().__init__(molecule, inp_file_obj, options, path, key)
        self.disp_num = disp_num
        self.file_not_found_behavior = f"Could not open output file for singlepoint: {self.disp_num}"

    def get_result(self):
        """ Use regex module to find and return energy with any necessary corrections

        Notes
        -----
        Ignores ValueError from _get_energy_float since success string should be found
        before this method is every called.

        """

        with open(f'{self.path}/output.dat') as f:
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
    """
    
    def __init__(self, molecule, inp_file_obj, options, disp_num=None, path=".", key=None):
        super().__init__(molecule, inp_file_obj, options, path, key)

        print(self.path)

        not_found = "Gradient calculation has failed."

        if disp_num:
            self.file_not_found_behavior = f"{not_found} for displacement {disp_num}"
        else:
            self.file_not_found_behavior = not_found
   
    def compute_result(self):
        self.write_input()
        self.run()
        print(f"checking for correct working dir: {os.getcwd()}")
        return self.get_result()

    def get_result(self):
        """ Gets the gradient according to method specified by user
    
        Returns
        -------
        np.ndarray
            shape: (natom, 3)
    
        """
        
        if self.options.gradient_file:
            with open(f'{self.path}/{gradient_file}') as f:
                grad_str = f.readlines()
        else:
            output_path = os.path.join(self.path, self.options.output_name)
        
            with open(output_path) as f:
                output = f.read()
            
            # add gradient regex to header regex supplied by user.
            label_xyz = r"(\s*\w?\w?(\s*-?\d*\.\d*){3})+"
            regex = self.options.gradient_regex + label_xyz
            grad_str = re.search(regex, output).group()
        
        return self.str_to_numpy(grad_str)

    def get_reference_energy(self):
        """ Get reference energy from gradient calculation """ 
        
        output_path = os.path.join(self.path, self.options.output_name)
        
        with open(output_path) as f:
            output = f.read()
    
        return self._get_energy_float(self.options.energy_regex, output) 

    def str_to_numpy(self, grad_output):
        # files might be formatted with comment or natom line. Ignore and grab the last natom 
        # lines

        grad_lines = grad_output.split("\n")
        # drop labels if present
        twoD_grad_str = [line.split()[-3:] for line in grad_lines[-self.molecule.natom:]]
        twoD_grad = np.asarray(twoD_grad_str).astype(float)
        return Matrix.from_array(twoD_grad) 
