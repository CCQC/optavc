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
lies here. Gradient, and Hessian are mostly going to loop of SinglePoint

Controls writing template files, running individual singlepoints,  
"""


import os
import re
import shutil
import copy
from abc import ABC, abstractmethod
from . import submitter


class Calculation(ABC):
    def __init__(self, molecule, inp_file_obj, options, path=".", key=None):
        self.molecule = molecule
        self.inp_file_obj = inp_file_obj
        self.options = copy.deepcopy(options)
        self.path = os.path.abspath(path)
        self.dict_obj = {}

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


class SinglePoint(Calculation):

    def __init__(self, molecule, inp_file_obj, options, path=".", disp_num=1, key=None):
        super().__init__(molecule, inp_file_obj, options, path)
        self.key = key
        self.disp_num = disp_num
        self.options.job_array_range = (1, 1)
    
    def write_input(self):
        """ Uses template.InputFile.make_input() to replace the geometry in
        the user provided template file. Writes input file to the singlepoints
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

    def run(self):
        """ Change to singlepoint directory. Effect is to invoke subprocess 
        Returns
        -------
        str : output captured from qsub *.sh """

        working_directory = os.getcwd()
        os.chdir(self.path)
        output = submitter.submit(self.options)
        os.chdir(working_directory)
        return output

    def get_energy_from_output(self):
        """ Fetch energy with any corrections needed.

        Returns
        -------
        float : requested energy
        
        Raises
        ------
        RuntimeError : No sucess string was found - job hasn't finished, stalled, or failed
        ValueError : get_last_energy() could not find the energy statement but a
            success statement was found. Check regex with tool such as - regexr.com.

        """ 

        status, output = self.check_status(self.options.success_regex, return_text=True)
        
        if status:
            energy = self.get_last_energy(self.options.energy_regex, output)
            correction = sum(self.get_last_energy(correction_regex, output)
                             for correction_regex in self.options.correction_regexes)
            # If no correction, adding zero. Add to correlation energy if 2 energies
            return energy + correction
        else:
            raise RuntimeError(f""" Could not find success string in output.dat 
                                SinglePoint job {self.disp_num} failed""")

    def check_status(self, status_str, return_text=False):
        """ Check for status_str. This is how optavc finds failed jobs. This information
        is necessary but not sufficient to resubmit a job on sapelo.

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

        """
        
        try:
            output_path = os.path.join(self.path, self.options.output_name)
            output_text = open(output_path).read()
        except FileNotFoundError as e:
            print(f"Could not open output file for singlepoint: {self.disp_num}")
            raise
        else:
            check = re.search(status_str, output_text)
            if return_text:
                return check, output_text
            return check
    
    # These two functions are purely here for the testing of the resub functionality
    def check_resub(self):
        """ Check/test the resubmission feature. Searches for the 'Giraffe' inserted by 'insert_Giraffe' function.
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
        """ Inserts the string 'Giraffe' into all output files. Useful for testing regex dependent methods as a proof of concept.
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
        with open(output_path,'w') as file:
            file.writelines(output_text)

    def get_last_energy(self, regex_str, output_text):
        try:
            return float(re.findall(regex_str, output_text)[-1])
        except (ValueError, IndexError) as e:
            if regex_str == '':
                return 0.0  # Yes, yes, I'm silencing an exception no one cares
            else:
                raise ValueError(f"Could not find energy for singlepoint {self.disp_num} using {regex_str}")
