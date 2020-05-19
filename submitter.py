import sys
import subprocess
from optavc.submit_template import template, progdict


def submit(options):
    """
	This is a very limited submit function. A template sh file
	is taken and formatted with queue and nthread information.
        This only works on SGE clusters.
	"""
    q = options.queue
    prog = options.program
    progname = prog.split("@")[0]
    job_num = int(options.job_array_range[1])
    odict = {
        'q': options.queue,
        'nslots':options.nslots,
        'jarray': '1-{}'.format(job_num),
        'tc': str(job_num),
        'progname':progname,
        'prog':prog,
        'cline':progdict[progname]
    }
    out = template.format(**odict)
    with open('optstep.sh', 'w') as f:
        f.write(out)
    subprocess.call('qsub optstep.sh', shell=True)


