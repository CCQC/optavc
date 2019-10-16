import numpy as np
import re
from . import regex
from .molecule import Molecule


class InputFile(object):
    """
  A formatable template for an input file that can place coordinates in the
  proper location in the input file.
  """
    def __init__(self, header, footer, body_template):
        self.header = header
        self.footer = footer
        self.body_template = body_template

    def make_input(self, geometry_array):
        """
    Generates an input_file string with the geometry replaced by the
    geometry_array.
    """
        coordinates = list(geometry_array.flatten())
        body = self.body_template.format(*coordinates)
        return self.header + body + self.footer


class TemplateFileProcessor(object):
    """
  Takes a template file and an options object for its contructor and creates
  the corresponding InputFile and Molecule objects, which are saved as class
  attributes.
  """
    def __init__(self, file_string, options):
        """
    :param file_string: a string of the template file
    :param options: an optavc options dictionary

    Generate an InputFile and Molecule
    """
        # Bagel does things diffrerently
        if 'bagel' in file_string[:100]:
            """
      Sample bagel geometry line
      {"atom" : "Li",  "xyz" : [ 0.0, 0.0,  1.0]},
      {"atom" : "F",   "xyz" : [ 0.0, 0.0, -1.0]}
      """
            import json
            jinp = json.loads(file_string)
            geom = ''
            for block in jinp['bagel']:
                if 'geometry' in block:
                    geom = block['geometry']
            if not geom:
                raise Exception('Could not find geometry')

            xyzstring = "units {:s}\n".format(options.input_units)
            placeholder = 'PLACEHOLDER'
            for line in geom:
                xyzstring += ('{:<2s} ' + '{:> 17.12f}' * 3 + '\n').format(
                    line['atom'], *line['xyz'])
                line['xyz'] = placeholder

            header = ''
            footer = ''
            body_str = '{ "bagel" : ' + json.dumps(jinp['bagel'],
                                                   indent=4) + '}'
            body_template = body_str.replace('{', '{{').replace(
                '}', '}}').replace('"' + placeholder + '"',
                                   '[{:> 17.12f}, {:> 17.12f}, {:> 17.12f}]')

        else:
            """
      Sample geometry line
      H     0.0 0.0 0.0
      O     0.0 0.0 1.0
      """
            geom_line_regex = regex.lsp_atomic_symbol + 3 * regex.lsp_signed_double + regex.lsp_endline
            geom_block_regex = regex.two_or_more(geom_line_regex)

            match = None
            for match in re.finditer(geom_block_regex, file_string,
                                     re.MULTILINE):
                pass
            if not match:
                raise Exception('Cannot find start of geometry')

            start, end = match.start(), match.end()
            coord_str = file_string[start:end]
            """
      Extract the contents of the current geometry block and use it to build a
      molecule -- the units of the geometry contained in the template file must
      be specified in options.input_units (default: "angstrom")
      """
            xyzstring = "units {:s}\n{:s}".format(options.input_units,
                                                  coord_str)

            header, footer = file_string[:start], file_string[end:]
            # Replace any curly braces with double braces to prevent formatting them
            coord_str = coord_str.replace('{', '{{').replace('}', '}}')
            body_template = re.sub('\s*(-?\d+\.?\d*)', ' {:> 17.12f}',
                                   coord_str)

        self.molecule = Molecule(xyzstring)
        self.input_file_object = InputFile(header, footer, body_template)


