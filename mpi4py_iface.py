from mpi4py import MPI
import os
import re
from .dask_iface import get_energy_from_output
#from .mpi4py_iface import compute,worker
from .executable import Executable,which 
COMM = MPI.COMM_WORLD
WORKTAG=0
DIETAG=1

def master(wi,func):
    """
    Used by master process to take a list of arguments and a function, then
    sow these out to worker processes. Collects return data from the processes.
    inputs:
        wi::list -> list of arguments to be passed into func
        func::function -> function to feed list of arguments into
    outputs:
        all_data::list(::float64) -> the output of func executed on all items of input wi    
    """
    all_data = []
    size = MPI.COMM_WORLD.Get_size()
    work_size = len(wi)
    current_work = Work(wi)
    COMM = MPI.COMM_WORLD
    status = MPI.Status()
    for i in range(1, size): 
        anext = current_work.get_next_item()
        if not anext: break
        COMM.send(obj=anext, dest=i, tag=WORKTAG)
    while True:
        print('receiving data ...')
        anext = current_work.get_next_item()
        if not anext: break
        data = COMM.recv(source=MPI.ANY_SOURCE, tag=MPI.ANY_TAG, status=status)
        all_data.append(data)
        COMM.send(obj=anext, dest=status.Get_source(), tag=WORKTAG)
    while len(all_data) < work_size:
        data = COMM.recv(source=MPI.ANY_SOURCE,tag=MPI.ANY_TAG,status=status)
        if status.Get_tag():
            print('OPTAVC+mpi@MASTER: error found - slaying all workers')
            slay()
            exit()
        all_data.append(data)
    print('all data collected')
    return all_data
     
    
def worker(do_work):
    """
    Used by worker processes. Makes the process enter an indefinite loop checking for work.
    Sends back to the Dies once kill signal is broadcast.
    inputs:
        do_work::function -> function to execute on any incoming data.
    outputs:
        None
    """
    comm = MPI.COMM_WORLD
    status = MPI.Status()
    while 1:
        data = comm.recv(source=0, tag=MPI.ANY_TAG, status=status)
        print('got work!')
        if status.Get_tag(): break
        odata = do_work(data)
        if odata[0] == 1:
            otag = DIETAG
        else:
            otag = WORKTAG
        comm.send(obj=do_work(data), tag=otag, dest=0)
        
class Work():
    def __init__(self, work_items):
        self.work_items = work_items[:] 
        
    def get_next_item(self):
        if len(self.work_items) == 0:
            return None
        return self.work_items.pop()
    
def slay():
    size = MPI.COMM_WORLD.Get_size()
    if COMM.rank == 0:
        for  i in range(1,size):
            COMM.send(obj=None,dest=i,tag=DIETAG)
            
def mpirun(options_obj):
    print(COMM.rank)
    if COMM.rank == 0:
        from optavc.optimize import Optimization
        optimization_obj = Optimization(options_obj)
        optimization_obj.run()
    else:
        worker(compute)
        
def mpi_print_out(text,outputname='output.mpi'):
    """
    Prints to mpi output file the input text.
    inputs:
        text::str -> text to print out
        path::str -> valid absolute path to output file
    outputs:
        none
    """
    with open('output.mpi','a') as f: f.write(text+'\n')
        
def compute(_singlepoint):
    """
    This function is called by worker processes to execute the task specified
    in _singlepoint. 
    inputs:
        _singlepoint::dict -> dictionary containing command to be executed, path to
                              folder to execute in, and so on.
                              
    outputs:
        (e,_singlepoint['index'])::tuple
        e::float64 -> computed energy of the singlepoint
        _singlepoint['index']::int64 -> place of this displacemint in the original singlepoint
                                        list, so that master process can rebuild in the right order.
    """
    wd = os.getcwd()
    os.chdir(_singlepoint['path'])
    os.system(_singlepoint['options']['command'])
    os.chdir(wd)
    fname = _singlepoint['path']+'/'+_singlepoint['options']['output_name']
    with open(_singlepoint['path']+'/'+_singlepoint['options']['output_name'], 'r') as f: cont = f.read()
    if re.search(_singlepoint['options']['energy_regex'],cont):
        e = re.findall(_singlepoint['options']['energy_regex'],cont)[-1]
    else:
        print('regex failed')
        e = 1
    return (e,_singlepoint['index'])
    
def to_dict(singlepoints):
    """
    Converts key information from optavc.SinglePoint object into a dictionary.
    This is needed s.t. the object can be pickled and passed over network.
    Order of output list is the same as input list.
    
    inputs:
        singlepoints::list(singlepoint::optavc.SinglePoint)
                        ->  list of singlepoint objects to be converted to dictionary
                            objects.
    outputs:
        _singlepoints::list(singlepoint::dict) -> list of dictionary objects containing 
                                                  information from input singlepoint objects."""
    _singlepoints = [singlepoint.to_dict() for singlepoint in singlepoints]
    for idx,val in enumerate(_singlepoints):
        _singlepoints[idx]['index'] = idx
    return _singlepoints

def hopper(flist,N=None,func=None,client=None):
    #function that steps through and executes a function func on a list of input values flist
    #over N workers. This avoids the 'jamming' problem to some extent.
    flist_copy = deepcopy(flist)
    outlist = []
    fn = flist_copy.pop #to move through list
    while len(flist_copy) > 0:
      #  print(len(flist_copy))
        if len(flist_copy) < N:
            n = len(flist_copy)
        else:
            n = N
      #  print(n)
        temp = [flist_copy.pop(0) for i in range(n)] #makes a list of the first n values in flist and deletes them
       # print(temp)
        temp = [delayed(func)(i) for i in temp]
        result = client2.compute(temp)
        result = client2.gather(result)
        outlist += result
    return outlist