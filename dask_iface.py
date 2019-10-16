"""
This is an attempt at an interface for optavc to use Dask for distributed computing
of single point energies. It doesn't work; I switched to using mpi4py for simplicity.
"""

from distributed import Client
import dask
import subprocess as sp
import os
import time
import re
from .executable import Executable

def connect_Client(path_to_scheduler):
    """
    inputs:
        path_to_scheduler -> str, eg /global/cscratch1/sd/md38294/scheduler3.json
    outputs:
        client -> Dask client object, to which jobs can be sown.
    """
    client = Client(scheduler_file=path_to_scheduler)
    return client

def setup(script):
    """
    runs a setup script that initializes scheduler, workers
    """
    sp.call(script)
def run_parallel(singlepoints, client):
    print('in dask_iface.run_parallel')
    """
    inputs:
        singlepoints -> list, list of single points as molecule objects
    outputs:
        future -> distributed.futures object, corresponds to the energies of 
                  the above singlepoints.
    """
    cwd = os.getcwd()
    _singlepoints = [singlepoint.to_dict() for singlepoint in singlepoints]
    lazy_energies = []
    
    print('mapping singlepoints')
    workers = client.scheduler_info()['workers']
    print(len(workers))
    #for _singlepoint in _singlepoints:
    #    lazy_result = dask.delayed(run_individual)(_singlepoint)
    #    lazy_energies.append(lazy_result)
    #energies = dask.compute(*lazy_energies)
    #energies = client.com(lazy_)
    tasks = [client.submit(run_individual, arg, workers=worker) for arg,worker in zip(_singlepoints,workers)]
    print(tasks)
    client.gather(tasks)
    exit()
    print('gathering singlepoints')

    do_continue = True
    #time.sleep(5)
    for _singlepoint in _singlepoints:
        print('checking singlepoint ... ')
        outcome = check_success(_singlepoint)
        if outcome == True:
            continue
        elif outcome == False:
            do_continue = False
            break
        elif outcome == None:
            do_continue = False
            break
    if not do_continue:
        return 1
    #energies = []
    #for _singlepoint in _singlepoints:
    #    e = get_energy_from_output(_singlepoint)
    #    print(e)
    #    energies.append(e)
    return energies

def check_success(_singlepoint,timeout=60):
    cont = None
    while cont is None:
        if os.path.isfile(_singlepoint['path']+'/'+_singlepoint['options']['output_name']):
            with open(str(_singlepoint['path']+'/'+_singlepoint['options']['output_name']),'r') as f: cont = f.read()
        else:
            time.sleep(5)
    success = re.search(_singlepoint['options']['success_regex'],cont)
    failure = re.search(_singlepoint['options']['fail_regex'],cont)
    t0 = time.time()
    t = time.time()
    while (not success) and (not failure) and (t - t0 < timeout):
        success = re.search(_singlepoint['options']['success_regex'],cont)
        failure = re.search(_singlepoint['options']['fail_regex'],cont)
        t = time.time()
    if success:
        return True
    elif failure:
        return False
    else:
        return None #timeout
    
def run_individual(_singlepoint):
    """
    This function is used in a dask distributed call, such as
       ` futures = client.map(run_individual,singlepoints) `
    
    inputs:
        singlepoint -> optavc.singlepoint object"""
    #import os
    working_directory = os.getcwd()
    os.chdir(_singlepoint['path'])
    
    #sp.call should block until the computation is complete.
    #sp.call("{}".format(_singlepoint['options']['prep_cmd']),shell=True)
    #sp.call("{}".format(_singlepoint['options']['command']),shell=True)
    executor = Executable(_singlepoint['options']['command'])
    executor()
    #proc = sp.Popen(_singlepoint['options']['command'].split())
    os.chdir(working_directory)
    e = 0#get_energy_from_output(_singlepoint)
    return e
    #return 0

def get_energy_from_output(_singlepoint):
        output_path = os.path.join(_singlepoint['path'], _singlepoint['options']['output_name'])
        print(output_path)
        output_text = open(output_path).read()
        if re.search(_singlepoint['options']['energy_regex'], output_text):
            try:
                get_last_energy = lambda regex: float(
                    re.findall(regex, output_text)[-1])
                energy = get_last_energy(_singlepoint['options']['energy_regex'])
                correction = sum(
                    get_last_energy(correction_regex)
                    for correction_regex in _singlepoint['options']['correction_regexes'])
                return energy + correction
            except:
                raise Exception(
                    "Could not find energy in {:s}.".format(output_path))
        else:
            print('regex not found - in optavc.dask_iface')
            raise Exception(
                "SinglePoint job at {:s} failed.".format(output_path))