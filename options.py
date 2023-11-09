import os
import socket
import copy
from typing import Union

# from .dask_iface import connect_Client


class Options(object):
    """ The only *required* options for a *standard* run of optavc are energy_regex and program. All others are either
    not required for all jobs or have default values.

    The required options for the extrapolation procedure are xtpl_templates, xtpl_regexes, and xtpl_basis_sets.
    energy_regex and template_file_path are NOT allowed to fill in xtpl_regexes and xtpl_templates.
    program is allowed fill in xtpl_programs.

    The required options for performing an additive correction are delta_templates and delta_regexes.
    again energy_regex and template_file_path are not allowed to fill in delta_regexes and delta_templates


    Notes
    -----
    This class is also responsible for setting options in Psi4 that are required for optavc to utilize Psi4
    properly. Common keywords are max_force_g_convergence, findif_points, hessian_write, cart_hess_read. etc

    These are keywords related to the finite difference procedure and geometry optimization. NOT keywords related to
    running a specific calculation: basis_set, e_convergence, etc.

    Attributes
    ----------

    template_file_path : string
        default : 'template.dat'

        string, interpretable as a path, to a template file

    backup_template : string or None
        default : None

        string, interpretable as a path to a secondary template file if the first has failed.
        This is only invoked when performing a restart. This is invoked either with
        *run_optavc("HESS", sow=False)* or *run_optavc("OPT", restart_iteration=<xx>)*
        For optimizations this only applies to the iteration we restart. It will not persist, so
        the template_file_path should also be updated to match backup_template. (Only backup_template will
        overwrite the currently written template files).

    energy_regex : string
        python 'raw' string. Should work with multiline mode. Should contain a group which returns
        the energy itself.

    self.correction_regexes : string
        default = ''

        python 'raw' string. Should work with multiline mode. Should contain a group which returns the energy.
        This is a simple additive correction to the energy. For instance (T) correlation energy if CCSD(T) is needed.
        Not usually needed.

    self.deriv_regex : string
        default = ''

        python 'raw' string. Should work with multiline mode. Uses a permissive regex to grab the actual values of a
        gradient. deriv_regex should be written to match the few lines before the gradient. i.e.

        Total Molecular Gradient:

    self.cluster : string
        default = setter
        Allowed names for the cluster are vulcan, sapelo, and sapelo_old which are SGE, SLURM, and PBS/TORQUE clusters.
        if not provided otpavc will use socket.gethostname() to determine what cluster the user is on.

    self.constraint : string
       default = ''
       Allowed values are Intel, EPYC, Intel|EPYC. MPI communication errors often happen with mixed node usage on 
       Sapelo so defining one or the other may help.

    self.nslots : int
        default 4

        How many threads or tasks the job should be run with. Used to create the cluster submission script

    self.threads : int
        default 1

        WARNING. Experimental. For programs that CLAIM to use mixed MPI and OpenMP parallelism set threads seperately
        from taks

    self.scratch : string
        default 'lscratch'

        Choose between running on local scratch or a network filesystem. Vulcan has only lscratch. Sapelo has both;
        however, lscratch space is limited.

    self.program : string
        default ""

        name of the program to calculations with orca, molpro, psi4, or cfour
        The name should at least be sufficiently long to load the module with. i.e. cfour@2.0+mpi is sufficient for
        vulcan load psi4 is also sufficient isntead of psi4@master.

    self.parallel : string
        default = setter

        For programs like cfour the submission script generated and module loaded by optavc depends on the version.
        Recognized values are mpi, serial, and mixed. serial encompasses openMP parallelism. Mixed uses both and is
        experimental.

        the setter will attempt first to determine the value for parallel from the name of the program. i.e. cfour2.0+mpi
        otherwise programs defaults are: mpi for orca and molpro. serial for psi4 and cfour.

    self.time_limit : string
        default 10:00:00

        time limit on vulcan is automatically 2 weeks and this overrides optavc's default.
    self.queue : string
        default gen4.q or batch

    self.email : bool or None
        Vulcan and Sapelo both use myid. If requred email is automatically determined by $USER
        EMAIL is only setup for the Sapelo cluster

    self.email_opts : string
        default = 'END,FAIL'

        See documentation for the clusters queueing system for valid values. Optavc will not check.
        The default is only value for SLURM

    self.memory : string
        default '32GB'

        How much total memory is needed for the Job. Include units. Only used for SAPELO

    self.name : string
        default STEP

        This name may be altered at various levels but is the main prefix for how optavc names jobs.
        This impacts both directories in the current working directory and job names on the cluster.

    self.files_to_copy : list[string]
        default []

        Copy files from the current working directory to the directories for each displacement.
        Useful for files like GENBAS which can be pulled by default from the cfour install but may need
        to be overridden

    self.input_name
        default 'input.dat'

        what should the template file be named when it is written into a directory.
        When running cfour the input file will eventually be named ZMAT but this may occur in a tmp directory

    self.output_name : string
        default 'output.dat'

    self.input_units : string
        default "angstrom"

        Make sure to set to bohr if the molecule in your template file. issues will occur and may not be easily
        recognizable

    self.point_group : string
        default None
        optavc will call psi4.reset_point_group(point_group) to make sure the symmetry is being conserved.

    self.dertype : string
        default ENERGY

        allowed values are ENERGY or 0, GRADIENT or 1, HESSIAN or 2. Optimizations can be done with 0, or 1.
        Hessians can be done with 0, 1, or 2

    self.deriv_file : string
        default 'output'

        What file should we look in to fetch the gradient or hessian. if 'output' the output file is serched with
        deriv_regex. Otherwise optavc attempts to read a gradient, or hessian file like cfour's GRD file.
        If program is cfour optavc will force use of the GRD file.

    self.mpi : bool
        default None

        WARNING Experimental. Legacy, unmaintained code for submitting singlepoints to slurm as a single mpi process

    self.job_array : bool
        defualt False

        Should calculations be submitted in an array or as individual jobs to the cluster. array submission is only
        supported if cluster is Vulcan. job_array will be set to False for Sapelo.

    self.resub : bool
        default False

        Prevents shut down of optavc if a calculation has failed by resubmitting to the cluster's queue. This only
        affects calculations that are run through the FiniteDifferenceCalc classes.

    self.resub_max : int
        default None

        How many times should a singlepoint be resubmitted. Some old molpro issues on specific Sapelo nodes required
        ths to be set to a relatively large integer. Be careful

    self.sleepy_sleep_time : int
        default 60

        Determines the frequency with which optavc will wake up and check the status of its jobs.

    self.xtpl : bool
        default None

        is an extrapolation to be performed.

    self.maxiter
        default 20

        This is optavc's internal maxiter. Optkings geom_maxiter should not be obeyed since gradients are being
        set manually

    self.xtpl_basis_sets : None or List[List[int]]
        This is a required keyword for performing an extrapolation. Optavc will fail is this is set unnecesarily
        without the other required keywords.

        list of lists of cardinal numbers for a basis set extrapolation. See composite gradient section for more
        details

        The first list corresponds to extrapolation of a correlated method, the second list is for HF.
        example [[4, 3], [5, 4, 3]]

    self.xtpl_templates : None or List[List[str]]
        This is a required keyword for performing an extrapolation. Optavc will fail is this is set unnecesarily
        without the other required keywords.

        list of lists of strings for templates for a basis set extrapolation. See composite gradient section for more details
        The first list corresponds to extrapolation of a correlated method, the second list is for HF.
        example [['template.dat', 'template.dat], ['template1.dat', 'template2.dat']]

    self.xtpl_regexes : None or List[List[str]
        This is a required keyword for performing an extrapolation. Optavc will fail is this is set unnecesarily
        without the other required keywords.

        list of lists of raw strings . See composite gradient section for more details
        The first list corresponds to extrapolation of a correlated method, the second list is for HF.
        example : [[r'mp2_qz', r'mp2_tz'] [r'hf_5z, r'hf_qz'']]

    self.programs : None or List[List[str]]
        default setter

        If no value is given. self.program will be applied to every calculation in the extrapolation procedure
        The first list corresponds to extrapolation of a correlated method, the second list is for HF.

    self.xtpl_names : None or List[List[str]]
        default setter

        list of names for each calculation that will be performed. Duplicates are allowed. Default names are dependent
        on the number of calculations being performed and templates supplied.

    self.xtpl_dertypes : None or List[List[str]]
        default [[self.dertype, self.dertype], [self.dertype, 'self.dertype]]

        list of strings or integers to determine the type of calculations being submitted. Energy, Gradient or Hessian.
        If no values are provided all calculations are assumed to match self.dertype which itself defaults to energy

    self.xtpl_queues : None or List[List[str]]
        default [[self.queue, self.queue], [self.queue, self.queue]]

        If no values are provided, falls back to self.queue which defaults to gen4.q or batch depending on self.cluster

    self.xtpl_nslots : None or List[List[int]]
        default [[self.nslots, self.nslots], [self.nslots, self.nslots]]

        see self.nslots for its default value

    self.xtpl_memories : None or List[List[str]]
        default [[self.memory, self.memory], [self.memory, self.memory]]

        see self.memory for its default

    self.xtpl_parallels : None or List[List[str]]
        default [[self.parallel, self.parallel], [self.parallel, self.parallel]]

        see self.parallel for defaults

    self.xtpl_time_limits : None or List[List[str]]
        default [[self.time_limit, self.time_limit], [self.time_limit, self.time_limit]]

        see self.time_limit for defaults

    self.xtpl_scratches: None or List[List[str]]
        default [[self.scratch, self.scratch], [self.scratch, self.scratch]]

        self.scratch for default

    self.xtpl_deriv_regexes : None or List[List[str]]
        default [[self.deriv_regex, self.deriv_regex], [self.deriv_regex, self.deriv_regex]]

        see.deriv_regex for default

    self.xtpl_deriv_files : None or List[List[str]]
        default [[self.deriv_file, self.deriv_file], [self.deriv_file, self.deriv_file]]

    self.scf_xtpl : bool
        default False

        If false the scf results will not be extrapolatied. The extrapolated correlated result will
        be added to the scf result of the highest cardinality. Performing HF calculations with smaller basis
        sets may still be required i.e. with gradients.

    """

    def __init__(self, **kwargs):

        self.template_file_path = kwargs.pop("template_file_path", "template.dat")
        self.energy_regex = kwargs.pop("energy_regex", "")
        self.correction_regexes = kwargs.pop("correction_regexes", "")
        self.deriv_regex = kwargs.pop("deriv_regex", None)
        self.backup_template = kwargs.pop("backup_template", None)
        # self.success_regex = kwargs.pop("success_regex", "")
        # self.fail_regex = kwargs.pop("fail_regex", "")
        self.findif_points = kwargs.get("findif_points", None)

        # Standard cluster options. defaults will be provided where able
        self.cluster = kwargs.pop("cluster", None)
        self.nslots = kwargs.pop("nslots", 4)
        self.threads = kwargs.pop("threads", 1)  # for mixed mpi(nslots)/omp(threads)
        self.scratch = kwargs.pop('scratch', 'SCRATCH')
        self.constraint = kwargs.pop('constraint', '') # no default
        self.parallel = kwargs.pop("parallel", "")  # default in setter
        self.program = kwargs.pop("program", "")  # no default
        self.time_limit = kwargs.pop("time_limit", "10:00:00")
        self.queue = kwargs.pop("queue", "")
        self.email = kwargs.pop("email", None)
        self.email_opts = kwargs.pop("email_opts", 'END,FAIL')
        self.memory = kwargs.pop("memory", "32GB")
        self.name = kwargs.pop("name", "STEP")

        self.files_to_copy = kwargs.pop("files_to_copy", [])
        self.input_name = kwargs.pop("input_name", "input.dat")
        self.output_name = kwargs.pop("output_name", None)
        self.input_units = kwargs.pop("input_units", "angstrom")
        self.point_group = kwargs.pop("point_group", None)

        # options to govern the workings on optavc
        self.dertype = kwargs.pop('dertype', None)
        self.deriv_file = kwargs.pop("deriv_file", 'output')
        self.mpi = kwargs.pop("mpi", None)
        self.job_array = kwargs.pop("job_array", False)
        self.resub = kwargs.pop("resub", False)
        self.resub_max = kwargs.pop("resub_max", 1)
        self.wait_time = kwargs.pop("wait_time", None)
        self.sleepy_sleep_time = kwargs.pop("sleepy_sleep_time", 60)
        self.maxiter = kwargs.pop("maxiter", 20)

        # options for running optimizations using xtpl procedure
        self.xtpl = None
        self.xtpl_basis_sets = kwargs.pop("xtpl_basis_sets", None)  # REQUIRED
        self.xtpl_templates = kwargs.pop("xtpl_templates", None)  # REQUIRED
        self.xtpl_regexes = kwargs.pop("xtpl_regexes", None)  # REQUIRED
        self.xtpl_programs = kwargs.pop("xtpl_programs", None)  # try to fall back to self.program
        self.xtpl_names = kwargs.pop("xtpl_names", None)  # HAS DEFAULT
        self.xtpl_dertypes = kwargs.pop("xtpl_dertypes", None)  # NON XTPL DEFAULT
        self.xtpl_queues = kwargs.pop("xtpl_queues", None)  # NON XTPL DEFAULT
        self.xtpl_nslots = kwargs.pop("xtpl_nslots", None)  # NON XTPL DEFAULT
        self.xtpl_memories = kwargs.pop("xtpl_memories", None)  # NON XTPL DEFAULT
        self.xtpl_parallels = kwargs.pop("xtpl_parallels", None)  # NON XTPL DEFAULT
        self.xtpl_time_limits = kwargs.pop("xtpl_time_limits", None)  # NON XTPL DEFAULT
        self.xtpl_scratches = kwargs.pop("xtpl_scratches", None)  # NON XTPL DEFAULT
        self.scf_xtpl = kwargs.pop("scf_xtpl", False)
        self.xtpl_deriv_regexes = kwargs.pop("xtpl_deriv_regexes", None)
        self.xtpl_deriv_files = kwargs.pop("xtpl_deriv_files", None)
        self.enforce_xtpl_option_consistency()

        # options for calculations with corrections (correlation correction, relativistic, etc)
        self.delta = None
        self.delta_templates = kwargs.pop("delta_templates", None)  # REQUIRED
        self.delta_regexes = kwargs.pop("delta_regexes", None)  # REQUIRED
        self.delta_programs = kwargs.pop("delta_programs", None)  # try to fall back to self.program
        self.delta_names = kwargs.pop("delta_names", None)  # HAS DEFAULT
        self.delta_dertypes = kwargs.pop("delta_dertypes", None)  # NON DELTA DEFAULT
        self.delta_queues = kwargs.pop("delta_queues", None)  # NON DELTA DEFAULT
        self.delta_nslots = kwargs.pop("delta_nslots", None)  # NON DELTA DEFAULT
        self.delta_memories = kwargs.pop("delta_memories", None)  # NON DELTA DEFAULT
        self.delta_parallels = kwargs.pop("delta_parallels", None)  # NON DELTA DEFAULT
        self.delta_time_limits = kwargs.pop("delta_time_limits", None)  # NON DELTA DEFAULT
        self.delta_scratches = kwargs.pop("delta_scratches", None)  # NON DELTA DEFAULT
        self.delta_deriv_regexes = kwargs.pop("delta_deriv_regexes", None)
        self.delta_deriv_files = kwargs.pop("delta_deriv_files", None)
        self.enforce_delta_options_consistency()

        if self.mpi is not None:
            # from .mpi4py import compute

            self.command = kwargs.pop("command")
            # self.submitter = compute
        try:
            Options.initialize_psi_options(kwargs)
        except ImportError as e:
            if kwargs.pop('ignore_psi4'):
                pass
            else:
                raise e

    @property
    def scratch(self):
        return self._scratch

    @scratch.setter
    def scratch(self, val):
        if val.upper() in ['LSCRATCH', 'SCRATCH']:
            self._scratch = val.upper()
        else:
            raise ValueError("scratch may be LCSRATCH or SCRATCH. Defaults to SCRATCH")

    @property
    def constraint(self):
        return self._constraint
 
    @constraint.setter
    def constraint(self, val=""):
        if val.upper() in ['', 'INTEL', 'EPYC', 'EPYC|INTEL']:
            self._constraint = val.upper()
        else:
            raise ValueError("constraint only set for Sapelo.")

    @property
    def program(self):
        return self._program

    @program.setter
    def program(self, val=""):
        prog = val.lower().split("@")
        self._program = prog[0]

        if prog[0] == 'fermi':
            raise NotImplementedError("Fermi submit scripts have not been finalized.")

        if self.parallel == "":
            if prog[0] in ['psi4', 'fermi']:
                self.parallel = 'serial'
            elif prog[0] in ['orca', 'molpro']:
                self.parallel = 'mpi'

        if not self.parallel:
            if '+mpi' in prog[-1]:
                self.parallel = 'mpi'
            elif 'serial' in prog[-1]:
                self.parallel = 'serial'
            elif '~mpi' in prog[-1]:
                self.parallel = 'serial'
            elif 'cfour' in prog[0]:
                self.parallel = 'serial' # should be safe default
            else:
                self.parallel = 'serial'

    @property
    def cluster(self):
        return self._cluster

    @cluster.setter
    def cluster(self, val):

        if val is None:
            hostname = socket.gethostname()
            if 'ss-sub' in hostname:
                self._cluster = 'SAPELO'
            elif 'vlogin' in hostname:
                self._cluster = 'VULCAN'
            else:
                self._cluster = 'HOST'
        elif isinstance(val, str):
            self._cluster = val.upper()
        else:
            self._cluster = None
            raise ValueError("Unknown cluster")

    @property
    def queue(self):
        return self._queue

    @queue.setter
    def queue(self, val):
        if not val:
            if self.cluster == 'VULCAN':
                self._queue = 'gen4.q'
            elif self.cluster == 'SAPELO':
                self._queue = 'batch'
            else:
                raise ValueError('Do not have a default queue for specified cluster'
                                 'Please specify a queue')
        else:
            self._queue = val

    @property
    def input_name(self):
        return self._input_name

    @input_name.setter
    def input_name(self, val):
        if self.program == 'cfour':
            self._input_name = 'ZMAT'
        else:
            self._input_name = val

    @property
    def output_name(self):
        return self._output_name

    @output_name.setter
    def output_name(self, val):
        if not val:
            if self.program == 'fermi':
                val = 'fermi.out'
            else:
                val = 'output.dat'

        self._output_name = val


    @property
    def wait_time(self):
        return self._wait_time

    @wait_time.setter
    def wait_time(self, val):
        if val:
            if self.cluster != 'SAPELO':
                raise ValueError(f"Cannot use 'wait_time' with current cluster {self.cluster}")
        self._wait_time = val

    @property
    def email(self):
        return self._email

    @email.setter
    def email(self, val):
        if not val:
            self._email = False
        elif val is True:
            self.email = "${USER}@uga.edu"
        else:
            self._email = val

    @property
    def deriv_file(self):
        return self._deriv_file

    @deriv_file.setter
    def deriv_file(self, val):

        if val == 'output':
            if self.program.upper() == 'CFOUR':
                if self.dertype == "HESSIAN":
                    val = "FCMFINAL"
                else:
                    val = "GRD"
        self._deriv_file = val

    @property
    def job_array(self):
        return self._job_array

    @job_array.setter
    def job_array(self, val):
        if self.cluster.upper() == 'VULCAN':
            self._job_array = val
        else:
            # ensure that job_array is False for SAPELO, SAP2TEST etc
            self._job_array = False

    @property
    def dertype(self):
        return self._dertype

    @dertype.setter
    def dertype(self, val):

        dertypes = ['ENERGY', 'GRADIENT', 'HESSIAN']

        if val is None:
            self._dertype = 'ENERGY'
        elif isinstance(val, str):
            if val.upper() in dertypes:
                self._dertype = val.upper()
            else:
                raise ValueError("Unable to determine type of calculation (dertype)")
        elif val in [0, 1, 2]:
            self._dertype = dertypes[val]
        else:
            self._dertype = 'ENERGY'
            raise ValueError("Unable to determine type of calculation (dertype)")

    @property
    def resub_max(self):
        return self._resub_max

    @resub_max.setter
    def resub_max(self, val):
        if not self.resub:
            self._resub_max = 0
        else:
            self._resub_max = val

    @property
    def xtpl_templates(self):
        return self._xtpl_templates

    @xtpl_templates.setter
    def xtpl_templates(self, val):
        if val is not None:
            Options.check_xtpl_format(val, "xtpl_templates")
        self._xtpl_templates = val

    @property
    def xtpl_regexes(self):
        return self._xtpl_regexes

    @xtpl_regexes.setter
    def xtpl_regexes(self, val):
        if val is not None:
            Options.check_xtpl_format(val, "xtpl_regexes")
        self._xtpl_regexes = val

    @property
    def xtpl_basis_sets(self):
        return self._xtpl_basis_sets

    @xtpl_basis_sets.setter
    def xtpl_basis_sets(self, val):
        if val is not None:
            Options.check_xtpl_format(val, "xtpl_basis_sets")
        self._xtpl_basis_sets = val

    @property
    def xtpl_programs(self):
        return self._xtpl_program

    @xtpl_programs.setter
    def xtpl_programs(self, val):
        if not val and not self.program:
            raise ValueError("No program provided in xtpl_programs. Can not fall back to "
                             "standard program option")
        val = Options.xtpl_setter_helper(val, self.program, "xtpl_programs")
        self._xtpl_program = val

    @property
    def xtpl_names(self):
        return self._xtpl_names

    @xtpl_names.setter
    def xtpl_names(self, val):

        if self.xtpl_templates is None:
            self._xtpl_names = None

        elif not val:
            tmp = [['large_c', 'intermed_c', 'small_c'],
                   ['large_ref', 'intermed_ref', 'small_ref']]

            if len(self.xtpl_basis_sets[0]) == 2:
                tmp[0].pop(1)
            else:
               raise ValueError("Too many entries for xtpl_basis_sets[0]. Psi4 only has"
                                "implemented two point extrapolation")


            # make sure there aren't too many names for the basis set
            # extrapolation being performed
            while len(self.xtpl_basis_sets[1]) < len(tmp[1]):
                tmp[1].pop(1)

            # unique names should only appear for unique templates
            names = [[''] * len(self.xtpl_templates[0]), [''] * len(self.xtpl_templates[1])]

            templates_seen = []
            for xtpl_set_itr, xtpl_set in enumerate(self.xtpl_templates):
                for template_itr, template_val in enumerate(xtpl_set):
                    # assign matches if not previously seen. use index from first match found
                    # look in the same set on inputs first. If get index from the preceeding set
                    # only two sets so (xtpl_set_itr - 1) should never go negative.
                    if not template_val in templates_seen:
                        templates_seen.append(template_val)
                        names[xtpl_set_itr][template_itr] = tmp[xtpl_set_itr][template_itr]
                    else:
                        safe_template_itr = Options.safe_itr(template_itr)
                        if template_val in xtpl_set[:safe_template_itr]:
                            index = xtpl_set.index(template_val)
                            names[xtpl_set_itr][template_itr] = tmp[xtpl_set_itr][index]
                        else:
                            safe_xtpl_itr = Options.safe_itr(xtpl_set_itr)
                            # already seen. item must be in previous set
                            index = self.xtpl_templates[safe_xtpl_itr].index(template_val)
                            names[xtpl_set_itr][template_itr] = tmp[safe_xtpl_itr][index]
            val = names
        else:
            val = Options.xtpl_setter_helper(val, "xtpl_names")
        self._xtpl_names = val

    @property
    def xtpl_nslots(self):
        return self._xtpl_nslots

    @xtpl_nslots.setter
    def xtpl_nslots(self, val):
        val = Options.xtpl_setter_helper(val, self.nslots, "xtpl_nslots", int_allowed=True)
        self._xtpl_nslots = val

    @property
    def xtpl_dertypes(self):
        return self._xtpl_dertypes

    @xtpl_dertypes.setter
    def xtpl_dertypes(self, val):
        val = Options.xtpl_setter_helper(val, self.dertype, "xtpl_dertypes")
        self._xtpl_dertypes = val

    @property
    def xtpl_queues(self):
        return self._xtpl_queues

    @xtpl_queues.setter
    def xtpl_queues(self, val):
        val = Options.xtpl_setter_helper(val, self.queue, "xtpl_queues")
        self._xtpl_queues = val

    @property
    def xtpl_memories(self):
        return self._xtpl_memory

    @xtpl_memories.setter
    def xtpl_memories(self, val):
        val = Options.xtpl_setter_helper(val, self.memory,  "xtpl_memories")
        self._xtpl_memory = val

    @property
    def xtpl_parallels(self):
        return self._xtpl_parallel

    @xtpl_parallels.setter
    def xtpl_parallels(self, val):
        # ignore default. Want user set value or program based default
        val = Options.xtpl_setter_helper(val, None, "xtpl_parallels")
        self._xtpl_parallel = val

    @property
    def xtpl_time_limits(self):
        return self._xtpl_time_limit

    @xtpl_time_limits.setter
    def xtpl_time_limits(self, val):
        val = Options.xtpl_setter_helper(val, self.time_limit, "xtpl_time_limits")
        self._xtpl_time_limit = val

    @property
    def xtpl_deriv_regexes(self):
        return self._xtpl_deriv_regexes

    @xtpl_deriv_regexes.setter
    def xtpl_deriv_regexes(self, val):
        val = Options.xtpl_setter_helper(val, self.deriv_regex, "xtpl_deriv_regexes")
        self._xtpl_deriv_regexes = val

    @property
    def xtpl_scratches(self):
        return self._xtpl_scratches

    @xtpl_scratches.setter
    def xtpl_scratches(self, val):
        val = Options.xtpl_setter_helper(val, self.scratch, "xtpl_scratches")
        self._xtpl_scratches = val

    @property
    def xtpl_deriv_files(self):
        return self._xtpl_deriv_files

    @xtpl_deriv_files.setter
    def xtpl_deriv_files(self, val):
        val = Options.xtpl_setter_helper(val, self.deriv_file, "xtpl_setter_helper")
        self._xtpl_deriv_files = val

    @property
    def delta_regexes(self):
        return self._delta_regexes

    @delta_regexes.setter
    def delta_regexes(self, val):
        if val is not None:
            Options.check_delta_format(val, "delta_regexes")
            Options.check_option_dtype(val, "delta_regexes", False)
        self._delta_regexes = val

    @property
    def delta_templates(self):
        return self._delta_templates

    @delta_templates.setter
    def delta_templates(self, val):
        if val is not None:
            Options.check_delta_format(val, "delta_templates")
            Options.check_option_dtype(val, "delta_templates", False)
        self._delta_templates = val

    @property
    def delta_programs(self):
        return self._delta_programs

    @delta_programs.setter
    def delta_programs(self, val):
        val = self.delta_setter_helper(val, self.program, "delta_programs")
        self._delta_programs = val

    @property
    def delta_dertypes(self):
        return self._delta_dertypes

    @delta_dertypes.setter
    def delta_dertypes(self, val):
        val = self.delta_setter_helper(val, self.dertype, "delta_dertypes")
        self._delta_dertypes = val

    @property
    def delta_queues(self):
        return self._delta_queues

    @delta_queues.setter
    def delta_queues(self, val):
        val = self.delta_setter_helper(val, self.queue, "delta_queues")
        self._delta_queues = val

    @property
    def delta_deriv_files(self):
        return self._delta_deriv_files

    @delta_deriv_files.setter
    def delta_deriv_files(self, val):
        val = self.delta_setter_helper(val, self.deriv_file, "delta_deriv_files")
        self._delta_deriv_files = val

    @property
    def delta_names(self):
        return self._delta_names

    @delta_names.setter
    def delta_names(self, val):

        if self.delta_templates is None:
            pass
        elif not val:
            tmp = [[f'delta_{itr}', f'ref_{itr}'] for itr in range(len(self.delta_templates))]

            val = copy.deepcopy(self.delta_templates)
            for sublist in val:
                for itr, item in enumerate(sublist):
                    sublist[itr] = ''

            templates_seen = []
            for delta_itr, delta_set in enumerate(self.delta_templates):
                for template_itr, template in enumerate(delta_set):
                    if template not in templates_seen:
                        templates_seen.append(template)
                        val[delta_itr][template_itr] = tmp[delta_itr][template_itr]
                    elif template in delta_set:
                        index = delta_set.index(template)
                        val[delta_itr][template_itr] = tmp[delta_itr][index]
                    else:
                        for prev_itr, prev_set in enumerate(self.delta_templates[:delta_set]):
                            if template in prev_set:
                                index = prev_set.index(template)
                                val[delta_itr][template_itr] = tmp[prev_itr][index]
                                break
        else:
            val = self.delta_setter_helper(val, "delta_names")

        self._delta_names = val

    @property
    def delta_nslots(self):
        return self._delta_nslots

    @delta_nslots.setter
    def delta_nslots(self, val):

        val = self.delta_setter_helper(val, self.nslots, "delta_nslots", int_allowed=True)
        self._delta_nslots = val

    @property
    def delta_memories(self):
        return self._delta_memory

    @delta_memories.setter
    def delta_memories(self, val):
        val = self.delta_setter_helper(val, self.memory, "delta_memories")
        self._delta_memory = val

    @property
    def delta_parallels(self):
        return self._delta_parallel

    @delta_parallels.setter
    def delta_parallels(self, val):
        # ignore default. Want user set value or program based default
        val = self.delta_setter_helper(val, None, "delta_parallels")
        self._delta_parallel = val

    @property
    def delta_time_limits(self):
        return self._delta_time_limit

    @delta_time_limits.setter
    def delta_time_limits(self, val):
        val = self.delta_setter_helper(val, self.time_limit, "delta_time_limits")
        self._delta_time_limit = val

    @property
    def delta_scratches(self):
        return self._delta_scratch

    @delta_scratches.setter
    def delta_scratches(self, val):
        val = self.delta_setter_helper(val, self.scratch, "delta_scratches")
        self._delta_scratch = val

    @property
    def delta_deriv_regexes(self):
        return self._delta_deriv_regexes

    @delta_deriv_regexes.setter
    def delta_deriv_regexes(self, val):
        val = self.delta_setter_helper(val, self.deriv_regex, "delta_deriv_regexes")
        self._delta_deriv_regexes = val

    def enforce_xtpl_option_consistency(self):
        """Make sure all required options are set, dertypes allows all required gradients to be
        computed, and all options get broadcast to full specification """

        xtpl_options = [self.xtpl_templates, self.xtpl_regexes, self.xtpl_basis_sets]

        if None in xtpl_options:
            for opt in xtpl_options:
                if opt is not None:
                    print("ERROR: either none or all of the following options must be set"
                          "xtpl_tempaltes, xtpl_regexes, xtpl_dertypes, and xtpl_basis_sets")
                    raise ValueError("Not all xtpl_options have been set ")
            return
        else:
            self.xtpl = True

        xtpl_additions = [self.xtpl_scratches,
                          self.xtpl_parallels,
                          self.xtpl_names,
                          self.xtpl_dertypes,
                          self.xtpl_memories,
                          self.xtpl_programs,
                          self.xtpl_nslots,
                          self.xtpl_queues,
                          self.xtpl_time_limits,
                          self.xtpl_deriv_regexes,
                          self.xtpl_deriv_files]

        xtpl_options = xtpl_options + xtpl_additions


        if len(self.xtpl_dertypes[0]) != len(self.xtpl_dertypes[1]) and 0 in self.xtpl_dertypes[0]:
            raise ValueError("Analytic gradients requested but the number of HF gradients does not"
                             "match the number of correlated gradients.")

        if len(self.xtpl_regexes[0]) == 1 and len(self.xtpl_templates[0]) == 1:
            raise ValueError(f"Cannot perform an extrapolation if xtpl_templates and "
                             "xtpl_regexes both contain only one entry for correlated calculations")

        # pad options out to two or three entries if necessary
        for option in xtpl_options:

            Options.pad_options_to_x_point_xtpl(option, self.xtpl_basis_sets)

            if len(option[0]) != len(self.xtpl_basis_sets[0]):
                raise ValueError(f"unable to fill out the options {option} to match the desired"
                                 "len{xtpl_basis_sets[0]} point extrapolation procedure")

    def enforce_delta_options_consistency(self):
        """Make sure combination or delta_tempalte and delta_regex makes sense and that all
         options get broadcast to the correct dimension """

        if self.delta_templates is None and self.delta_regexes:
            raise ValueError("Did not provide delta_regexes")
        elif self.delta_regexes is None and self.delta_templates:
            raise ValueError("Did not provide delta_templates")
        elif self.delta_templates is None and self.delta_regexes is None:
            self.delta = False
            return
        else:
            if None in self.delta_programs and not self.program:
                raise ValueError("Delta options have been set; however, no default delta_program or program has been" 
                                 "set")
            self.delta = True

        for itr, template_set in enumerate(self.delta_templates):
            if len(template_set) == 1 and len(self.delta_regexes[itr]) == 1:
                raise ValueError("If only one template is provided. Two regexes must be provided")

        delta_options = [self.delta_templates,
                         self.delta_programs,
                         self.delta_queues,
                         self.delta_nslots,
                         self.delta_memories,
                         self.delta_dertypes,
                         self.delta_scratches,
                         self.delta_parallels,
                         self.delta_time_limits,
                         self.delta_names,
                         self.delta_deriv_regexes,
                         self.delta_deriv_files]

        # ensure all options have two entries for each list, copying if necessary
        # under assumption user would like an option to apply to both calculations
        for option in delta_options:
            for itr, delta_set in enumerate(option):
                if len(delta_set) == 1:
                    option[itr] = [delta_set[0], delta_set[0]]

    @staticmethod
    def pad_options_to_x_point_xtpl(options, template):
        """If one option is given to apply to multiple calculations broadcast to 2 or 3 for
        the appropriate extrapolation type

        Notes
        -----
        optavc current uses only xtpl_basis_sets for this method

        """

        # Pad out to 2 or 3. i.e. if xtpl_templates = [['template1'], ['template2']]
        # for a two point extrapolation xtpl_templates will become:
        # [['template1', 'template1'], ['template2', 'template2']]
        for itr, xtpl_set in enumerate(options):
            if len(xtpl_set) == 1:
                x_point_xtpl = len(template[itr])
                options[itr] = [xtpl_set[0] for _ in range(x_point_xtpl)]

    @staticmethod
    def check_option_dtype(option, options_str, int_allowed):

        for opt_set in option:
            for itr, item in enumerate(opt_set):
                if isinstance(item, str):
                    continue
                elif int_allowed and isinstance(item, int):
                    continue
                elif item is None:
                    continue
                else:
                    raise ValueError(f"{options_str} should be a list[list[string]]")

    @staticmethod
    def xtpl_setter_helper(val, default=None, opt_name="", int_allowed=False):
        """ For an xtpl option that has a default provided by the options standard version check
        that formatting is of the type [[options], [options]] or broadcast a single option to the
        that format. Then check that the option is of the appropriate type (None, str) """

        if val is None:
            val = default

        if isinstance(val, list):
            Options.check_xtpl_format(val, opt_name)
        else:
            val = [[val], [val]]

        Options.check_option_dtype(val, opt_name, int_allowed)
        return val

    @staticmethod
    def check_xtpl_format(val: list, opt_name):

        if len(val) > 2:
            raise ValueError(f"{opt_name} cannot contain more than two lists")

        for itr, val_set in enumerate(val):

            if not isinstance(val_set, list):
                raise ValueError(f"{opt_name} must! be a list of lists")

            if len(val_set) not in [1, 2, 3]:
                if itr == 0:
                    raise ValueError(f"The entry in {opt_name} for correlation energy"
                                     "extrapolation must contain 1 or 2 strings")
                else:
                    raise ValueError(f"The entry in {opt_name} for reference energy"
                                     "extrapolation must contain 1, 2, or 3 strings")

    def delta_setter_helper(self, val, default=None, opt_name="", int_allowed=False):
        """ Ensure lists obey delta formatting and data types. Broadcast non iterable inputs
        to the delta format """

        if val is None:
            val = default

        if isinstance(val, list):
            Options.check_delta_format(val, opt_name)
        else:
            try:
                max_specified = max(len(self.delta_templates), len(self.delta_regexes))
                val = [[val]] * max_specified
            except TypeError:
                return val
        Options.check_option_dtype(val, opt_name, int_allowed)
        return val

    @staticmethod
    def check_delta_format(val: list, opt_name):
        """Check that a list is of the appropriate format for performing corrections """
        for itr, val_set in enumerate(val):
            if isinstance(val_set, list):
                if len(val_set) > 2:
                    raise ValueError(
                        f"entry: {itr} for {opt_name} should contain either 1 "
                        f"or 2 elements.")
            else:
                raise ValueError(f"{opt_name} must be a list of lists")

    @staticmethod
    def initialize_psi_options(kwargs):
        import psi4
        for key, value in kwargs.items():
            key = key.upper()
            psi4.core.print_options()
            if key in psi4.core.get_global_option_list():
                psi4.core.set_global_option(key, value)
                psi4.core.print_out("{:s} set to {:s}\n".format(
                    key,
                    str(value).upper()))
            elif type(value) is dict:
                try:
                    for subkey, subvalue in value.items():
                        subkey = subkey.upper()
                        psi4.core.set_local_option(key, subkey, subvalue)
                        psi4.core.print_out("{:s} {:s} set to {:s}\n".format(
                            key, subkey,
                            str(subvalue).upper()))
                except:
                    raise Exception(
                        "Attempt to set local psi4 option {:s} with {:s} failed.".format(key,
                                                                                         str(value)))
            else:
                raise Exception("Unrecognized keyword {:s}".format(str(key)))

    @staticmethod
    def safe_itr(option_itr):
        if option_itr - 1 < 0:
            return 0
        else:
            return option_itr - 1
