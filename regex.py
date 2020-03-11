# fundamental components
character = r'[a-zA-Z]'
unsigned_integer = r'\d+'
signed_double = r'-?\d+\.\d+'
whitespace = r'\s'
endline = r'\n'


# fundamental functions
def capture(string):
    return r'({:s})'.format(string)


def maybe(string):
    return r'(?:{:s})?'.format(string)


def zero_or_more(string):
    return r'(?:{:s})*'.format(string)


def one_or_more(string):
    return r'(?:{:s})+'.format(string)


def two_or_more(string):
    return r'(?:{:s}){{2,}}'.format(string)


# some commonly used strings -- lsp indicates "zero or more *l*eading *sp*aces"
lsp_endline = zero_or_more(whitespace) + endline
lsp_word = zero_or_more(whitespace) + two_or_more(character)
lsp_signed_double = zero_or_more(whitespace) + signed_double
lsp_atomic_symbol = zero_or_more(whitespace) + character + maybe(character)


class BagelRegex:
    """
    Regular expression library for Bagel outputs

    Includes samples of the output for comparisson
    """
    """
      9        -75.02529220          0.00000001           0.00
               o DIIS                                        0.00
               o Diag                                        0.00
               o Post process                                0.00
               o Fock build                                  0.00
     10        -75.02529220          0.00000000           0.00
  
    * SCF iteration converged.

    * Permanent dipole moment:
    """
    hf = r"\d+\s+(-?\d+\.\d+)\s+0\.\d+\s+\d+\.\d+\n\s*\n    \* SCF iteration converged\."
    """
  === Relativistic FCI iteration ===

                 * sigma vector                            4.17e-03
                 * davidson                                2.77e-04
                 * error                                   1.13e-05
                 * denominator                             4.83e-06
      0   0  *     -99.37091199     5.56e-16      0.00
      0   1  *     -99.37091199     1.62e-15      0.00
      0   2  *     -99.37091199     1.54e-15      0.00
      0   3  *     -99.37091199     4.07e-15      0.00
      0   4  *     -99.36906267     2.29e-15      0.00
      0   5  *     -99.36906267     1.84e-15      0.00

     * ci vector, state   0
       b22  (0.0403514045,-0.0394344882)
    """
    casscf = r"\* denominator\s+\d+\.\d+e-\d+\n\s+\d+\s+\d+\s+\*\s+(-\d+\.\d+)\s+\d+\.\d+e-\d+\s+\d+\.\d+"
    """
       - MRCI energy evaluation                 5839.09

        0   0  -190.78090477     0.00000000      0.00

       - MRCI+Q energy evaluation                  0.00
    """
    mrci = r"- MRCI energy evaluation\s+\d+\.\d+\n\n\s+0   0\s+(-\d+\.\d+)\s+\d+\.\d+\s+\d+\.\d+"
