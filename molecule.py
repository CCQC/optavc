import psi4
import numpy as np
import re
from . import regex
from . import masses

bohr2angstrom = 0.52917721067


class Molecule(object):
    def __init__(self, arg):
        try:
            # if arg is a psi4.Molecule, convert it to a molecule string
            molecule_string = arg
            if type(arg) is psi4.core.Molecule:
                arg.update_geometry()
                molecule_string = arg.create_psi4_string_from_molecule()
            assert type(molecule_string) is str
            # predefine regexes
            units_regex = "units" + regex.capture(
                regex.lsp_word) + regex.lsp_endline
            label_regex = regex.capture(
                regex.lsp_atomic_symbol
            ) + 3 * regex.lsp_signed_double + regex.lsp_endline
            xyz_regex = regex.lsp_atomic_symbol + 3 * regex.capture(
                regex.lsp_signed_double) + regex.lsp_endline
            # define Molecule attributes
            self.units = re.search(units_regex,
                                   molecule_string).group(1).strip().lower()
            self.labels = [
                label_match.group(1).strip().upper()
                for label_match in re.finditer(label_regex, molecule_string)
            ]
            self.geom = np.array(
                [[float(coord) for coord in xyz_match.groups()]
                 for xyz_match in re.finditer(xyz_regex, molecule_string)])
            self.masses = [masses.get_mass(label) for label in self.labels]
            self.natom = len(self.labels)
            assert self.units in ("angstrom", "bohr")
        except:
            raise Exception(
                "Invalid argument \n{:s}\n passed to Molecule constructor.".
                format(xyzstring))

    def set_units(self, units):
        if units == "angstrom" and self.units == "bohr":
            print(self.geom)
            self.units = "angstrom"
            self.geom *= bohr2angstrom
        elif units == "bohr" and self.units == "angstrom":
            self.units = "bohr"
            self.geom /= bohr2angstrom

    def __len__(self):
        return self.natom

    def __iter__(self):
        for label, xyz in zip(self.labels, self.geom):
            yield label, xyz

    def __str__(self):
        ret = "units {:s}\n".format(self.units)
        fmt = "{:2s} {: >15.10f} {: >15.10f} {: >15.10f}\n"
        for label, coords in self:
            ret += fmt.format(label, *coords)
        return ret

    def __repr__(self):
        return str(self)

    def copy(self):
        return Molecule(str(self))

    def set_geometry(self, geom, geom_units=None):
        #print(geom)
        if geom_units is None: geom_units = self.units
        self.units = geom_units
        self.geom = geom

    def cast_to_psi4_molecule_object(self):
        #psi4.efp_init() # JPM - Maybe the original use case needed this library?
        mol = psi4.core.Molecule.from_string(str(self))
        mol.update_geometry()
        return mol


