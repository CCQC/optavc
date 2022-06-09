import math
import socket 

import psi4
import pytest

import optavc

PSI_CCSDT = r"\s*\*\sCCSD\(T\)\stotal\senergy\s+=\s(-\d+.\d+)"
MOLPRO_MP2 = r"\s*\!RHF-RMP2\senergy\s+(-\d+.\d+)"
MOLPRO_CCSDT = r"\s*\!RHF-UCCSD\(T\)\senergy\s*(-\d+.\d+)" 
PSI_SCF = r"\s*Reference\sEnergy\s+=\s+(-\d+.\d+)"
PSI_MP2 = r"\s+\sTotal\sEnergy\s+=\s+(-\d+.\d+)"
PSI_MP2_GRAD_EN = r"\s*DF-MP2\sTotal\sEnergy\s\(a\.u\.\)\s*:\s*(-\d*.\d*)" 
PSI_SCF_GRAD_EN = r"\s*\s\sTotal\sEnergy\s*=\s*(-\d*.\d*)"
C4_ENERGY = r"\s*The\sfinal\selectronic\senergy\sis\s*(-\d*.\d*)"
PSI4_GRAD = r"\s*-Total\s*[Gg]radient:\n\s*Atom[XYZ\s]*[-\s]*"

def test_psi4_driver():
    """ Runs mp2/CBS for O2 and compare against psi4 """   

    options = {"energy_regex": PSI_SCF,
               "xtpl_templates": [["templates/psi_O2_mp2qz.dat", "templates/psi_O2_mp2tz.dat"],
                                  ["templates/psi_O2_mp2qz.dat", "templates/psi_O2_mp2tz.dat"]], 
               "xtpl_names": [["mp2_qz", "mp2_tz"], ["mp2_qz", "mp2_tz"]],
               "xtpl_basis_sets": [[4, 3], [4, 3]],
               "xtpl_regexes": [[PSI_MP2], [PSI_SCF]],
               "xtpl_programs": "psi4",
               "max_force_g_convergence": 1e-6
    }

    if 'vlogin' in socket.gethostname():
        options.update({"xtpl_queues": "gen4.q"}) 
    if 'ss-sub' in socket.gethostname():
        options.update({"xtpl_queues": "batch"}) 
    
    gradient, energy, molecule = optavc.run_optavc('opt', options)   

    assert math.isclose(energy, -150.200365229198, rel_tol=0, abs_tol=1e-6)

def test_xtpl_molpro():
    """Run molpro CCSD(T) + mp2/CBS - no comparison """
    
    options = {"energy_regex": PSI_SCF,
               "xtpl_templates": [["templates/psi_O2_mp2qz.dat", "templates/psi_O2_mp2tz.dat"],
                                  ["templates/psi_O2_mp2qz.dat", "templates/psi_O2_mp2tz.dat"]],
               "xtpl_regexes": [[PSI_MP2], [PSI_SCF]],
               "xtpl_names": [["mp2_qz", "mp2_tz"], ["mp2_qz", "mp2_tz"]],
               "xtpl_basis_sets": [[4, 3], [4, 3]],
               "xtpl_programs": "psi4",
               "scf_xtpl": False,
               "delta_templates": [["templates/molpro_O2_ccsdt.dat"]],
               "delta_regexes": [[MOLPRO_CCSDT, MOLPRO_MP2]],
               "delta_programs": "molpro@2010.1.67+mpi",
               "max_force_g_convergence": 1e-7
    }
    
    if 'vlogin' in socket.gethostname():
        options.update({"delta_queues": "gen4.q", "xtpl_queues": "gen4.q"}) 
    if 'ss-sub' in socket.gethostname():
        options.update({"delta_queues": "batch", "xtpl_queues": "batch"}) 

    gradient, energy, molecule = optavc.run_optavc('opt', options) 

    p4mol = molecule.cast_to_psi4_molecule_object() 

    assert math.isclose(p4mol.nuclear_repulsion_energy(), 28.028875150649082, rel_tol=0, abs_tol=1e-4)


def test_xtpl_cfour():
    """cfour CCSD(T) + mp2/CBS using gradients - compare to psi4 w/cfour interface """

    options = {"energy_regex": PSI_SCF,
               "xtpl_templates": [["templates/psi_O2_mp2qz_grad.dat", "templates/psi_O2_mp2tz_grad.dat"], 
                                  ["templates/psi_O2_scfqz_grad.dat", "templates/psi_O2_scftz_grad.dat"]],
               "xtpl_regexes": [[PSI_MP2], [PSI_MP2]],
               "xtpl_dertypes": "gradient",
               "xtpl_programs": "psi4",
               "xtpl_names": [["mp2_qz", "mp2_tz"], ["scf_qz", "scf_tz"]],
               "xtpl_deriv_regexes": PSI4_GRAD,
               "xtpl_basis_sets": [[4, 3], [4, 3]],
               "delta_templates": [["templates/cfour_O2_ccsdt.dat", "templates/cfour_O2_mp2.dat"]],
               "delta_regexes": [[C4_ENERGY, C4_ENERGY]],
               "delta_dertypes": "gradient",
               "delta_programs": [["cfour@2+mpi", "cfour@2~mpi"]],
               "delta_names": [["c4_grad1", "c4_grad2"]],
               "max_force_g_convergence": 1e-6
    }

    if 'vlogin' in socket.gethostname():
        options.update({"delta_queues": "gen4.q", "xtpl_queues": "gen4.q"}) 
    if 'ss-sub' in socket.gethostname():
        options.update({"delta_queues": "batch", "xtpl_queues": "batch"}) 

    gradient, energy, molecule = optavc.run_optavc("opt", options)

    assert math.isclose(energy, -149.700965645798, rel_tol=1.e-05)
 
