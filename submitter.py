import sys
import subprocess


def submit(options):
    """
	This is a very limited submit function. A template sh file
	is taken and formatted with queue and nthread information.
	The template file is a molpro submit script.
        This only works on SGE clusters.
	"""
    q = options.queue
    prog = options.program
    job_num = int(options.job_array_range[1])
    with open('/home/vulcan/mmd01986/bin/optavc/submit_template.sh', 'r') as f:
        temp = f.read()
    out = temp.format(**{
        'q': options.queue,
        'jarray': '1-{}'.format(job_num),
        'tc': str(job_num)
    })
    with open('optstep.sh', 'w') as f:
        f.write(out)
    subprocess.call('qsub optstep.sh', shell=True)
