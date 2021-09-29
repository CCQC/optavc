import optavc
from optavc import xtpl, options, template



def test_delta_options():

    energy_regex = 'a'
    molpronfc = 'b'
    molprofc = 'c'

    template_dummy_string = """0 1
    C	0.0000000	0.0000000	0.5889820
    C	0.0000000	1.2631860	-0.2599400
    C	0.0000000	-1.2631860	-0.2599400
    H	0.8730160	0.0000000	1.2426200
    H	-0.8730160	0.0000000	1.2426200
    H	0.0000000	2.1608190	0.3554840
    H	0.0000000	-2.1608190	0.3554840
    H	0.8793880	1.2973360	-0.9027060
    H	-0.8793880	1.2973360	-0.9027060
    H	-0.8793880	-1.2973360	-0.9027060
    H	0.8793880	-1.2973360	-0.9027060
    """

    input1 = 'templates/template1.dat'
    input2 = 'templates/template2.dat'
    input3 = 'templates/template.dat'

    delta_opts = {'program'            : "psi4", 
                  'delta_templates'    : [[input1, input2],[input3, input3]],
                  'delta_regexes'      : [[energy_regex, energy_regex],[molpronfc, molprofc]],
                  'delta_nslots'       : [[10,2],[4,4]],
                  'delta_programs'     : [['psi4@master','psi4@master'],["molpro", "molpro"]],
                  'delta_memories'     : [['50GB','5GB'],['10GB','10GB']],
                  'delta_names'        : [['ccsd_t','mp2dz'],['fc','fc']],
                  'delta_queues'       : [['batch','batch'],['batch','batch']],
                  'delta_parallels'    : [['serial','serial'],['mpi','mpi']],
                  'delta_dertypes'     : [['gradient','gradient'],['energy','energy']]}

    opts_obj = options.Options(**delta_opts)
    template_obj = template.TemplateFileProcessor(template_dummy_string, opts_obj)
    molecule = template_obj.molecule

    delta_obj = xtpl.Delta("GRADIENT", molecule, opts_obj)
