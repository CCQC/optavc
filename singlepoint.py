import os
import re
import shutil


class SinglePoint(object):
    def __init__(self, molecule, inp_file_obj, options, submitter, path=".", key=None):
        self.molecule = molecule
        self.inp_file_obj = inp_file_obj
        self.options = options
        self.submitter = submitter
        self.path = os.path.abspath(path)
        self.key = key
        self.submitter=submitter
        self.dict = {}

    def to_dict(self):
        self.dict['path'] = self.path
        self.dict['options'] = {}
        #for i in self.options:
        self.dict['options']['command'] = self.options.command
        #self.dict['options']['prep_cmd'] = self.options.prep_cmd
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
        self.submitter(self.options)
        os.chdir(working_directory)

    def get_energy_from_output(self):
        output_path = os.path.join(self.path, self.options.output_name)
        output_text = open(output_path).read()
        if re.search(self.options.success_regex, output_text):
            try:
                get_last_energy = lambda regex: float(
                    re.findall(regex, output_text)[-1])
                energy = get_last_energy(self.options.energy_regex)
                correction = sum(
                    get_last_energy(correction_regex)
                    for correction_regex in self.options.correction_regexes)
                return energy + correction
            except:
                raise Exception(
                    "Could not find energy in {:s}.".format(output_path))
        else:
            raise Exception(
                "SinglePoint job at {:s} failed.".format(output_path))
