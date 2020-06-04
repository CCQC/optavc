import sys
import subprocess
from . import submit_template


def submit(options):
    """ This is a very limited submit function. A template sh file
	is taken and formatted with queue and nthread information.
    This only works on SGE and PBS clusters. Clusters are identified by name 
    and not by submission type 
    """

    out = make_sub_script(options)

    with open('optstep.sh', 'w') as f:
        f.write(out)
    subprocess.call('qsub optstep.sh', shell=True)


def make_sub_script(options):
    """ Add necessary options to the submission script """

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
        'cline': submit_template.progdict[progname]
    }

    if options.cluster.upper() == 'SAPELO':
        odict.update({'mod_load': submit_template.sapelo_mod_load.get(progname),
                      'email': options.email,
                      'email_opts': options.email_opts,
                      'memory': options.memory,
                      'time': options.time_limit,
                      'name': options.name
                      })
        out = submit_template.sapelo_template.format(**odict)
        return out
    elif options.cluster.upper() != 'VULCAN':
        print("No cluster provided or cluster not yet supported.")
        print("Trying to continue by defaulting to Vulcan")
    
    odict.update({'tc': str(job_num)})
    if options.job_array:
        out = submit_template.vulcan_template.format(**odict)
    else:
        out = submit_template_sp.vulcan_template.format(**odict)
    return out
