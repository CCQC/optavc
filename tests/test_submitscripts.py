import pytest
import optavc

# This is my simple, dirty way to make sure we're actually generating submit scripts for all programs
# correctly and choosing between for instance molpro 24 and molpro 21. cfour serial and mpi
# note how simple the sprogram specs I'm using are. A better test would be to run an energy with each
# submit script

@pytest.mark.parametrize("program", [("molpro@2024"),
                        ("molpro@2021"),
                        ("cfour@2.1-mpi"),
                        ("cfour@2.1"),
                        ("psi4"),
                        ("orca")])
def test_programs(program):

    options_kwargs = { 
        'input_name'         : "input.dat",
        'output_name'        : "output.dat",
        "program": program,
        'cluster': 'Sapelo',
    }

    options = optavc.options.Options(**options_kwargs)
    options.job_array_range = (1, 1)  # This is a poor design choice
    cluster = optavc.cluster.Cluster("SAPELO")
    sub_script = cluster.make_sub_script(options)

    with open(f"./sub_templates/{program}_template.sh", "r") as f:
        ref_template = str(f.read())
    assert sub_script == ref_template

