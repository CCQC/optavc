"""
import sys
import subprocess
from . import submit_template
from . import submit_template_sp


def submit(options):
    \""" This is a very limited submit function. A template sh file
    is taken and formatted with queue and nthread information.
    This only works on SGE and PBS clusters. Clusters are identified by name
    and not by submission type
    \"""

    pipe =
     subprocess.PIPE

    if options.cluster != 'SAPELO':
        process = subprocess.Popen(['qconf', '-secl'], stdout=pipe, stderr=pipe, encoding='UTF-8')
        synced_procs = str(process.stdout).split("\n")
        if len(synced_procs) == 6:
            vulcan_submit_individual()
            return
    out = make_sub_script(options)

    with open('optstep.sh', 'w') as f:
        f.write(out)
    # subprocess.pipe collects all output. encoede to usable string
    process = subprocess.Popen('qsub optstep.sh', stdout=pipe, stderr=pipe, shell=True,
                                encoding='UTF-8')
    print(process.stdout)
    return process.stdout[:-1]


def vulcan_submit_individual(queued_singlepoints: list):
    \""" Must be working from the gradients directory. Gradient.path

    Parameters
    ----------
    queued_singlepoints: List[Singlepoint]

    Notes
    -----
    This has been made a seperate method so that all processes can be managed together
    Vulcan performs resubmission assuming all jobs have finished before the optavc process resumes
    \"""
    # TODO for resubmission via Popen we need to create them all upfront

    out = make_sub_script(options)
    processes = []
    targets = [f'{singlepoint.path}/optstep.sh' for singlepoint in queued_singlepoints]

    for submit_script in targets:
        with open(submit_script, 'w+') as f:
            f.write(out)
        processes.append(subprocess.Popen(['qsub', submit_script]))

    # wait for all processes to finish
    for proc in processes:
        proc.communicate()


def make_sub_script(options):
    \""" Add necessary options to the submission script \"""

    q = options.queue
    prog = options.program
    progname = prog.split("@")[0]
    job_num = int(options.job_array_range[1])
    cluster = options.cluster

    odict = {
        'q': options.queue,
        'nslots': options.nslots,
        'jarray': '1-{}'.format(job_num),
        'progname': progname,
        'prog': prog,
        'cline': submit_template.progdict[progname],
        'name': options.name
    }

    if options.cluster.upper() == 'SAPELO':
        odict.update({'mod_load': submit_template.sapelo_mod_load.get(progname),
                      'email': options.email,
                      'email_opts': options.email_opts,
                      'memory': options.memory,
                      'time': options.time_limit
                      })
        # Sapelo defaults to individual runs
        out = submit_template_sp.sapelo_template.format(**odict)
        return out
    elif options.cluster.upper() != 'VULCAN':
        print("No cluster provided or cluster not yet supported.")
        print("Trying to continue by defaulting to Vulcan")

        odict.update({'tc': str(job_num)})
        # out = submit_template.vulcan_template.format(**odict)
        if options.job_array:
            out = submit_template.vulcan_template.format(**odict)
        else:
            out = submit_template_sp.vulcan_template.format(**odict)
        return out

"""