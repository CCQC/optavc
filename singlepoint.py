import os
import re
import shutil
from . import submitter


class SinglePoint(object):
    def __init__(self, molecule, inp_file_obj, options, path=".", key=None):
        self.molecule = molecule
        self.inp_file_obj = inp_file_obj
        self.options = options
        self.path = os.path.abspath(path)
        self.key = key
        self.dict = {}

    def to_dict(self):
        self.dict['path'] = self.path
        self.dict['options'] = {}
        # for i in self.options:
        if self.options.mpi is not None:
            self.dict['options']['command'] = self.options.command
        # self.dict['options']['prep_cmd'] = self.options.prep_cmd
        self.dict['options']['output_name'] = self.options.output_name
        self.dict['options']['energy_regex'] = self.options.energy_regex
        self.dict['options'][
            'correction_regexes'] = self.options.correction_regexes
        self.dict['options']['success_regex'] = self.options.success_regex
        self.dict['options']['fail_regex'] = self.options.fail_regex
        self.dict['path'] = self.path
        return self.dict

    def write_input(self):
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
        working_directory = os.getcwd()
        os.chdir(self.path)
        submitter.submit(self.options)
        os.chdir(working_directory)

    def get_energy_from_output(self):

        try:
            output_path = os.path.join(self.path, self.options.output_name)
            output_text = open(output_path).read()
        except FileNotFoundError as e:
            print(str(e))
            print("Could not open output file")
            raise

        if re.search(self.options.success_regex, output_text):

            energy = get_last_energy(self.options.energy_regex, output_path, output_text)

            correction = sum(get_last_energy(correction_regex, output_path, output_text)
                             for correction_regex in self.options.correction_regexes)
            # If no correction, adding zero. Add to correlation energy if 2 energies
            return energy + correction
        else:
            print("Could not find success string in output.dat")
            raise RuntimeError("SinglePoint job at {:s} failed.".format(output_path))

    def check_success(self, return_text=False):
        try:
            output_path = os.path.join(self.path, self.options.output_name)
            output_text = open(output_path).read()
        except FileNotFoundError as e:
            print(str(e))
            print("Could not open output file")
            raise
        check = re.search(self.options.success_regex, output_text)
        if return_text:
            return check, output_text
        return check
    
    # These two functions are purely here for the testing of the resub functionality
    def check_resub(self):
        output_path = os.path.join(self.path, self.options.output_name)
        output_text = open(output_path).read()
        return re.search(self.options.resub_regex, output_text)
    
    def insert_Giraffe(self):
        output_path = os.path.join(self.path, self.options.output_name)
        output_text = open(output_path).read()
        output_text += 'Giraffe'
        with open(output_path,'w') as file:
            file.writelines(output_text)

def get_last_energy(regex_str, output_path, output_text):
    try:
        return float(re.findall(regex_str, output_text)[-1])
    except (ValueError, IndexError) as e:
        if regex_str == '':
            return 0.0  # Yes, yes, I'm silencing an exception no one cares
        else:
            print(str(e))
            raise ValueError(f"Could not find energy in {output_path} using {regex_str}")
