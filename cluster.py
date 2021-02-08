"""
Cluster is meant to encapsulate all differences between cluster systems for submission and
resubmission of jobs.

"""

import subprocess
import re
import os

from .submitscripts.sge import sge, vulcan_programs
from .submitscripts.pbs import pbs, sapelo_old_programs
from .submitscripts.slurm import slurm, sapelo_programs


class Cluster:
    """ To add a new cluster one must add the following strings to cluster_attributes

        add a submission command for a submission sciprt.

        a queue_info command as a list of strings with None at the last index (to be replaced by
        the job's_id. Should the name and state of a single job.

        a regex_string for the job's 'state' or None (if None must add code in job_finished 
        as explicit as conditional)

        a regex_string for the jobs's name to which pulls out the singlepoint number (number must be
        in second capture group 2 see below examples) ex. STEP--00-1

        # wait time is a more general pause than resub_delay. resub_delay minimizes
        # the up-time of optavc. 'wait_time' makes sure the cluster has enough time
        # to see jobs
    """
    def __init__(self, cluster_name):
        self.cluster_name = cluster_name

        attributes = self.cluster_attributes(self.cluster_name)
        self.submit_command = attributes.get('submit')
        self.queue_info = attributes.get('queue_info')
        self.job_state = attributes.get('job_state')
        self.job_name = attributes.get('job_name')
        self.job_id = attributes.get('job_id')
        self.resub_delay = attributes.get('resub_delay')
        self.wait_time = attributes.get('wait_time')

    @staticmethod
    def cluster_attributes(cluster_name):

        # Please add a cluster here or if optavc can't find your jobs
        # on a cluster please adjust 'resub_delay' and 'wait_time'

        attributes = {'VULCAN': {'submit': 'qsub',
                                 'queue_info': ['qacct', '-j', None],
                                 'job_state': None,
                                 'job_name': r'jobname\s+.*(--\d*)?-(\d*)',
                                 'job_id': r'Your\s*job(?:-array)?\s*(\d*)',
                                 'resub_delay': lambda sleep: max(10, sleep),
                                 'wait_time': 5},
                      'SAPELO_OLD': {'submit': 'qsub',
                                     'queue_info': ['qstat', '-f', None],
                                     'job_state': r'\s*job_state\s=\sC',
                                     'job_name': r'\s*Job_Name\s=\s*.*(\-+\d*)?\-(\d*)',
                                     'job_id': r'(\d*)\.sapelo2',
                                     'resub_delay': lambda sleep: max(60, sleep),
                                     'wait_time': 5},
                      'SAPELO': {'submit': 'sbatch',
                                   'queue_info': ['sacct', '-X', '--format=JobID,JobName%60,STATE',
                                                  '-j', None],
                                   'job_state': None,
                                   'job_name': r'\s.+(--\d*)?-(\d+)',
                                   'job_id': r'\.*(\d+)',
                                   'resub_delay': lambda sleep: max(60, sleep),
                                   'wait_time': 30}}

        return attributes.get(cluster_name)

    def submit(self, options):
        """ This is a very limited submit function. A template sh file
        is taken from the submitscripts dir, formatted with make_sub_script(), and
        then run using the cluster's submit_command
        """

        out = self.make_sub_script(options)

        if len(options.name) > 60 and self.cluster_name == 'SAPELO':
            raise ValueError(f"Your Job's Name is too long please shorten by "
                             f"{len(options) - 60} characters or increase formatting space in "
                             f"`cluster_attributes()` for SAP2TEST")

        with open('optstep.sh', 'w+') as f:
            f.write(out)

        submit_command = self.submit_command
        pipe = subprocess.PIPE
        process = subprocess.run([submit_command, './optstep.sh'], stdout=pipe, stderr=pipe,
                                 encoding='UTF-8')

        # subprocess.pipe collects all output.
        # run will wait for array process to finish. Individual submissions will return immediately
        # from qsub so lack of parallel execution for run is inconsequential

        if process.stderr:
            print(process.stderr)
            print(os.getcwd())
            raise RuntimeError(f"\n{submit_command} command has FAILED. see {submit_command} STDERR"
                               " above\n")

        text_output = process.stdout
        return self.get_job_id(text_output, options.job_array)

    def query_cluster(self, job_id, job_array=True):
        """ use subprocess to get detailed information on a single job. output must be interpreted
        in cluster by cluster basis.

        Parameters
        ----------
        job_id

        Returns
        -------
        str: Output from cluster's command sacct, qstat -f, qacct -j. Can be None for qacct -j if
            job has not finished.

        """

        pipe = subprocess.PIPE
        self.queue_info[-1] = job_id  # last spot is held as None until job_id is ready
        # encoding UTF-8 will make stderr and stdout be of type str (not bytes)
        process = subprocess.run(self.queue_info, stdout=pipe, stderr=pipe, encoding='UTF-8')

        if process.stderr:

            if self.cluster_name == 'VULCAN':
                # qacct is only command which can see finished jobs. However, querying for a running
                # job produces stderr
                return False, 0

            print(process.stderr)
            raise RuntimeError(f"Error encountered trying to run {' '.join(self.queue_info)}")

        output = process.stdout
        job_state = self.job_finished(output)
        
        if not job_array:
            job_number = self.get_job_number(output)
        else:
            job_number = None

        return job_state, job_number

    def get_job_id(self, submit_output, job_array=False):
        """ Use regex to grab job_id. Regexes should be written for the stdout for the cluster's
        submit command

        Parameters
        ----------
        submit_output: str
            output from qsub, sbatch or similar command
        job_array: bool
            If True we don't need to lookup the job id

        Returns
        -------
        str

        """

        if not submit_output and job_array:
            raise RuntimeError(f"No output from {self.submit_command}. Cannot find job_id")

        if self.job_id:
            return re.search(self.job_id, submit_output).group(1)
        else:
            raise NotImplementedError("Cannot identify job_id on this cluster")

    def get_job_number(self, output):
        """ Parse output of the `job_info` command for job number number. All cluster's
        currently use regex to simply fetch the number

        Parameters
        ----------
        output: str
            unmodified output from queue_info command

        Returns
        -------
        int: number corresponding to the singlepoint run in 1 based indexing. Singlepoint.disp_num
        is 0 indexed

        """

        if self.job_name:
            try:
                job_number = int(re.search(self.job_name, output).group(2))
            except (TypeError, AttributeError):
                print("Can not find the singlepoint's disp_num check the regex and output below")
                print(self.job_name)
                print(output)
                raise
            else:
                return job_number
        else:
            raise NotImplementedError("Encountered cluster with no job_name regex")

    def job_finished(self, output):
        """ Determine whether a job is no longer queued or running on the cluster

        Parameters
        ----------
        output : str
            unmodified output from queue_info

        Returns
        -------
        bool : True if job is done

        Notes
        -----
        either use regex to look for pattern indicating job has finished or must supply cluster
        specific check in this method

        """

        job_state = False

        if self.job_state:
            # regex must be able to identify ANY finished job. None otherwise
            job_state = re.search(self.job_state, output)
        else:
            if self.cluster_name == 'VULCAN':
                if output:
                    job_state = True
            elif self.cluster_name == 'SAPELO':
                # simple check for substring in output
                if not ("PENDING" in output or "RUNNING" in output):
                    job_state = True
        print(f"state: {job_state}")
        print(f"output: {output}")
        return job_state

    def get_template(self, job_array=False, email=None, parallel='serial'):
        """ Only vulcan currently uses array submission. All other programs only submit
        singlepoints individually

        Parameters
        ----------
        job_array: bool, optional

        Returns
        -------
        str: ready to be dumped to file
        """

        if self.cluster_name == "VULCAN":
            if job_array:
                return sge.sge_array
            else:
                return sge.sge_basic
        elif self.cluster_name == "SAPELO_OLD":
            if email:
                return pbs.pbs_email
            return pbs.pbs_basic
        elif self.cluster_name == "SAPELO":
            
            if parallel in ['mpi', 'mixed']:
                if email:
                    return slurm.slurm_mpi_email
                return slurm.slurm_mpi
            else:
                if email:
                    return slurm.slurm_email
                return slurm.slurm_basic
        else:
            raise NotImplementedError("Please add a new template or label new cluster as SGE, PBS, "
                                      "or SLURM")

    def make_sub_script(self, options):
        """ Fill a template file with needed options for each cluster

        Parameters
        ----------
        options: options.Options

        """

        template = self.get_template(options.job_array, options.email, options.parallel)

        progname = options.program
        scratch = 'scratch'
        job_num = int(options.job_array_range[1])
        # cluster = self.options.cluster

        odict = {
            'q': options.queue,
            'nslots': options.nslots,
            'jarray': '1-{}'.format(job_num),
            'progname': progname,
            'name': options.name,
            'threads': options.threads
        }

        if self.cluster_name in ['SAPELO', "SAPELO_OLD"]:

            scratch = options.scratch.lower()

            odict.update({'memory': options.memory,
                          'time': options.time_limit})

            if options.email:
                odict.update({'email_opts': options.email_opts})

            if self.cluster_name == 'SAPELO':

                # choose program string
                if progname == 'molpro':
                    constraint = 'Intel'
                else:
                    constraint = 'EPYC|Intel'

                prog = sapelo_programs.progdict.get(options.parallel).get(scratch).get(progname)
                odict.update({'prog': prog, 'constraint': constraint})

            else:
                prog = sapelo_old_programs.progdict.get(options.parallel).get(scratch).get(progname)
                odict.update({'prog': prog})

        elif self.cluster_name == 'VULCAN':
            
            prog = vulcan_programs.progdict.get(options.parallel).get(scratch).get(progname)
            odict.update({'prog': prog})

            if options.job_array:
                odict.update({'tc': str(job_num)})

        return template.format(**odict)

    def enforce_job_array(self, original):
        """ Check qconf in case -sync processes have all been used. Otherwise job_array should be
        False

        Returns
        -------
        bool: value for job_array

        """
        pipe = subprocess.PIPE
        if self.cluster_name == 'VULCAN':
            process = subprocess.Popen(['qconf', '-secl'], stdout=pipe, stderr=pipe,
                                       encoding='UTF-8')
            # Two lines for formatting. 4 lines for processes of which 1 is scheduler
            if len(process.stdout.readlines()) >= 6:
                return False
            return original
        return False


# sge_template = ["""#!/bin/sh
# #$ -q {q}
# #$ -N {name}
# #$ -S /bin/sh
# #$ -cwd
# """,
# """. /etc/profile.d/modules.sh
# 
# # Disable production of core dump files
# ulimit -c 0
# 
# echo ""
# echo "***********************************************************************"
# echo " Starting job:"
# echo ""
# echo "    Name:              "$JOB_NAME
# echo "    ID:                "$JOB_ID
# echo "    Hostname:          "$HOSTNAME
# echo "    Working directory: "$SGE_O_WORKDIR
# echo ""
# echo "    Submitted using:   optavc "
# echo "***********************************************************************"
# 
# 
# vulcan load {prog}
# 
# export NSLOTS={nslots}
# 
# {cline}"""]
# 
# sge_array = """#$ -sync y
# #$ -t {jarray}
# #$ -tc {tc}
# """
# 
# pbs_template = ["""#PBS -S /bin/bash
# #PBS -q {q}
# #PBS -N {name}
# #PBS -l nodes=1:ppn={nslots}:Intel
# #PBS -l mem={memory}
# #PBS -l walltime={time}
# """,
# """cd $PBS_O_WORKDIR/
# echo "PBS_JOBID is $PBS_JOBID"
# 
# {mod_load}
# export NSLOTS={nslots}
# time {cline}
# # ignored newline - do not remove"""]
# 
# pbs_email = """#PBS -M {email}
# #PBS -m {email_opts}"""
# 
# slurm_template = ["""#!/bin/bash
# #SBATCH --partition={q}
# #SBATCH --job-name={name}
# #SBATCH --ntasks=1
# #SBATCH --cpus-per-task={nslots}
# #SBATCH --time={time}
# #SBATCH --mem={memory}
# """,
# """\ncd $SLURM_SUBMIT_DIR
# export OMP_NUM_THREADS={nslots}
# export NSLOTS={nslots}
# 
# {mod_load}
# 
# time {cline}
# # ignored newline -- do not remove"""]
# 
# slurm_email = ["""#SBATCH --mail-user={email}
# #SBATCH --mail-type={email_opts}"""]
# 
# sge_array_template = [sge_template[0], sge_array, sge_template[-1]]
# pbs_email_template = [pbs_template[0], pbs_email, pbs_template[-1]]
# slurm_email_template = [slurm_template[0], slurm_email, slurm_template]
# 
# progdict = {
#     "molpro": "molpro -n $NSLOTS --nouse-logfile --no-xml-output -o output.dat input.dat",
#     "psi4": "psi4 -n $NSLOTS"
# }
# 
# vulcan_load = {
#     "molpro": "molpro@2010.1.67+mpi",
#     "psi4": "psi4@master"
# }
# 
# sapelo_load_old = {
#     "molpro": "export PATH=$PATH:/work/jttlab/molpro/2010/bin/",
#     "psi4": "module load PSI4/1.3.2_conda"
# }
# 
# sapelo_load = {
#     "molpro": "export PATH=$PATH:/work/jttlab/molpro/2010/bin",
#     "psi4": "module load PSI4/1.3.2_conda"
# }
# 
# sapelo_scratch_load = {
#     "molpro": """export PATH=$PATH:/work/jttlab/molpro/2010/bin
# """,
#     "psi4": """module load PSI4/1.3.2_conda""", 
#     "cfour_mpi": """module load cfour/2.1-iompi-2018a-mpi""",
#     "cfour_serial": """module load cfour/2.1-iompi-2018a-serial """
#     "mrcc": """ """
# }
# 
# vulcan_scratch_load = {
#     "molpro": """ """,
#     "psi4": """ """,
#     "cfour": """ """,
#     "mrcc": """ """
# }
# 
