import random

import pytest

from optavc.cluster import Cluster

def sge_queries(names, completed):
    """ Simulate vulcan cluster by returning nothing if Job has not completed 
        (failure is complete) 
    """   
    
    for index, name in enumerate(names):
        if index in completed:
            yield vulcan.format(name=name)
        else:
            yield ""

def pbs_queries(names, completed):
    """ Generator to fill state and name into a mock sapelo qstat output """
    
    for index, name in enumerate(names):

        if index in completed:
            state = "C"
        else:
            state = random.choice(("R", "Q"))    

        yield sapelo.format(name=name, state=state)


def slurm_queries(names, completed):

    for index, name in enumerate(names):
        
        if index in completed:
            state = "COMPLETED"
        else:
            state = random.choice(("PENDING", "RUNNING"))
            print(state)

        yield sap2test.format(name=name, state=state)

@pytest.mark.parametrize("cluster", ["VULCAN", "SAPELO", "SAP2TEST"])
@pytest.mark.parametrize("name, number, completed", [('STEP--00', 8, [8, 2]), 
                                                     ('STEP--01', 8, [6, 7]), 
                                                     ('STEP--10', 3, [1]), 
                                                     ('STEP--00', 4, [1, 2]), 
                                                     ('STEP--03', 67, [40, 50, 66]), 
                                                     ("HESS", 4, [1, 2, 3, 4]), 
                                                     ("HESS", 4, [3, 2]), 
                                                     ('HESS', 1036, [1032]), 
                                                     ('ijfffads_fjfjaa-99', 4, [3])])
@pytest.mark.no_calc
def test_job_query(cluster, name, number, completed):
    

    cluster_obj = Cluster(cluster)

    query_methods = {'VULCAN': sge_queries, 'SAPELO': pbs_queries, 'SAP2TEST': slurm_queries}
    query_method = query_methods.get(cluster)
    names = [{'name': f"{name}-{id}"} for id in range(1, number + 1)]

    for index, job_info in enumerate(query_method(names, completed)):
       
        if not job_info:
            assert True  # vulcan doesn't return anything
            return    
 
        try:
            assert cluster_obj.get_job_number(job_info) == index + 1
        except AssertionError:
            print("Failed to correctly identify disp_num on Vulcan - SGE cluster")
            raise
        else:
            state = cluster_obj.job_finished(job_info)
                
            if state:
                try:
                    assert index in completed
                except AssertionError:
                    print("Job should not have been marked complete")
            else:
                if index in completed:
                    print("Job should have been marked complete ")
                    raise ValueError 


@pytest.mark.parametrize("cluster", ["VULCAN", "SAPELO", "SAP2TEST"])
@pytest.mark.parametrize("job_id", [random.randint(1000000, 9999999) for i in range(5)])
@pytest.mark.parametrize("job_name", ["STEP--00-1", "STEP--01", "HESS", "stupidly_long_molecule-name_-with_extra-949"])
@pytest.mark.no_calc
def test_job_id(cluster, job_id, job_name):

    cluster_obj = Cluster(cluster)
    id_strings = {"VULCAN": sge_submit, "SAPELO": pbs_submit, "SAP2TEST": slurm_submit}
    id_string = id_strings.get(cluster)
    
    if cluster == "VULCAN":
        id_output = id_string.format(**{"name": job_name, "job_id": job_id})
    else:
        id_output = id_string.format(**{"job_id": job_id})

    assert int(cluster_obj.get_job_id(id_output)) == job_id

sapelo = """
    Job_Name = {name}
    Job_Owner = agh66737@sapelo2-sub2.ecompute
    resources_used.cput = 00:00:08
    resources_used.vmem = 0kb
    resources_used.walltime = 00:00:04
    resources_used.mem = 888kb
    resources_used.energy_used = 0
    job_state = {state}
    queue = batch
    server = dispatch.ecompute
    Checkpoint = u
    ctime = Tue Sep 22 09:49:29 2020
    Error_Path = sapelo2-sub2.ecompute:/home/agh66737/mjolnir_local/optavc/tes
    ts/STEP04/2/optavc_test--04-2.e3292573
    exec_host = n220/8-11
    Hold_Types = n
    Join_Path = n
    Keep_Files = n
    Mail_Points = a
    mtime = Tue Sep 22 09:50:34 2020
    Output_Path = sapelo2-sub2.ecompute:/home/agh66737/mjolnir_local/optavc/te
    sts/STEP04/2/optavc_test--04-2.o3292573
    Priority = 0
    qtime = Tue Sep 22 09:49:29 2020
    Rerunable = True
    Resource_List.nodes = 1:ppn=4:Intel
    Resource_List.mem = 10gb
    Resource_List.walltime = 00:10:00
    Resource_List.nodect = 1
    session_id = 132984
    Shell_Path_List = /bin/bash
    Variable_List = MOAB_BATCH=,MOAB_CLASS=batch,MOAB_GROUP=jttlab,
    MOAB_JOBID=3292573,MOAB_JOBNAME=optavc_test--04-2,
    MOAB_MACHINE=dispatch,MOAB_NODECOUNT=1,MOAB_NODELIST=n220,
    MOAB_PARTITION=Moab_Sapelo2,MOAB_PROCCOUNT=4,
    MOAB_SUBMITDIR=/home/agh66737/mjolnir_local/optavc/tests/STEP04/2,
    MOAB_TASKMAP=n220:4,MOAB_USER=agh66737,PBS_O_QUEUE=batch,
    PBS_O_HOME=/home/agh66737,PBS_O_LOGNAME=agh66737,
    PBS_O_PATH=/usr/local/apps/gb/PSI4/1.3.2/bin:/usr/local/apps/gb/PSI4/
    1.3.2:/usr/local/apps/eb/Miniconda3/4.4.10-fresh:/usr/local/apps/eb/Mi
    niconda3/4.4.10-fresh/bin:/usr/local/bin:/opt/apps/torque/6.1.1.1/bin:
    /opt/apps/torque/6.1.1.1/sbin:/usr/lib64/qt-3.3/bin:/opt/apps/moab/9.1
    .3/bin:/usr/bin:/usr/local/sbin:/usr/sbin:/opt/puppetlabs/bin:/opt/sin
    gularity/bin:/opt/dell/srvadmin/bin:/usr/tools/bin:/home/agh66737/py_s
    cripts:/home/agh66737/.local/bin:/home/agh66737/bin,
    PBS_O_MAIL=/var/spool/mail/agh66737,PBS_O_SHELL=/bin/bash,
    PBS_O_LANG=en_US.UTF-8,
    PBS_O_WORKDIR=/home/agh66737/mjolnir_local/optavc/tests/STEP04/2,
    PBS_O_HOST=sapelo2-sub2.ecompute,PBS_O_SERVER=dispatch.ecompute
    euser = agh66737
    egroup = jttlab
    queue_type = E
    etime = Tue Sep 22 09:49:29 2020
    exit_status = 0
    submit_args = ./optstep.sh
    start_time = Tue Sep 22 09:50:30 2020
    start_count = 1
    fault_tolerant = False
    comp_time = Tue Sep 22 09:50:34 2020
    job_radix = 0
    total_runtime = 5.469600
    submit_host = sapelo2-sub2.ecompute
    init_work_dir = /home/agh66737/mjolnir_local/optavc/tests/STEP04/2
    request_version = 1
    req_information.task_count.0 = 1
    req_information.lprocs.0 = 4
    req_information.total_memory.0 = 10485760kb
    req_information.memory.0 = 10485760kb
    req_information.thread_usage_policy.0 = allowthreads
    req_information.hostlist.0 = n220:ppn=4
    req_information.task_usage.0.task.0.cpu_list = 1,3,5,7
    req_information.task_usage.0.task.0.mem_list = 1
    req_information.task_usage.0.task.0.cores = 0
    req_information.task_usage.0.task.0.threads = 4
    req_information.task_usage.0.task.0.host = n220
"""

vulcan = """
==============================================================
qname        gen3.q              
hostname     n014                
group        hfs                 
owner        agh66737            
project      NONE                
department   defaultdepartment   
jobname      {}   
jobnumber    403515              
taskid       undefined
account      sge                 
priority     0                   
qsub_time    Fri Sep 18 17:02:32 2020
start_time   Fri Sep 18 17:02:36 2020
end_time     Fri Sep 18 17:02:53 2020
granted_pe   NONE                
slots        1                   
failed       15  : in epilog
exit_status  0                   
ru_wallclock 17           
ru_utime     24.649       
ru_stime     1.802        
ru_maxrss    167108              
ru_ixrss     0                   
ru_ismrss    0                   
ru_idrss     0                   
ru_isrss     0                   
ru_minflt    103102              
ru_majflt    0                   
ru_nswap     0                   
ru_inblock   8                   
ru_oublock   77744               
ru_msgsnd    0                   
ru_msgrcv    0                   
ru_nsignals  0                   
ru_nvcsw     14926               
ru_nivcsw    74                  
cpu          26.451       
mem          27.408            
io           0.633             
iow          0.000             
maxvmem      1.573G
arid         undefined
"""

sap2test = """
       JobID                                                      JobName      State 
------------        ----------------------------------------------------- ---------- 
35326               {name}                                                {state}
"""

sge_submit = """
Your job {job_id} ("{name}") has been submitted
"""

slurm_submit = """
Submitted batch job {job_id}
"""

pbs_submit = """
{job_id}.sapelo2
"""

