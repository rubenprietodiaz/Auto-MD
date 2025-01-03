import os
import shutil
import argparse
import random

def parse_arguments():
    parser = argparse.ArgumentParser(description="Setup your MD simulation after PyMemDyn equilibration.")
    parser.add_argument("-t", "--simulation-time", type=int, help="Simulation time in nanoseconds (default: 25 ns).", default=25)
    parser.add_argument("-rt", "--runtime", type=int, help="Runtime in hours (default: 36).", default=36)
    parser.add_argument("-C", "--cluster", choices=["CSB", "CESGA", "TETRA"], default="TETRA", help="Choose the cluster (default: TETRA).")
    parser.add_argument("-n", "--num-replicas", type=int, help="Number of replicas for the MD simulations (default: 3).", default=3)
    return parser.parse_args()

def copy_files_in_directory(directory, destination_folder):
    """Iterate over folders and copy required files for MD simulation."""
    for root, dirs, _ in os.walk(directory):
        for dir in dirs:
            current_folder = os.path.join(root, dir)
            for replica in range(args.num_replicas):
                replica_folder = os.path.join(destination_folder, f"{dir}_{replica + 1}")
                copy_files(current_folder, replica_folder)
    create_submit_script(destination_folder)
    print(f"Folder '{destination_folder}' created. Run 'cd {destination_folder}' and 'sh submit_md.sh' to start simulations.")

def copy_files(folder, destination_folder):
    """Copy necessary files for MD simulation to the destination folder."""
    required_files = ["prod.mdp", "topol.top", "index.ndx", "topol.tpr"]
    if all(os.path.isfile(os.path.join(folder, file)) for file in required_files) and os.path.exists(os.path.join(folder, "finalOutput", "confout.gro")):
        #print(f"All required files are present in '{folder}'.")
        os.makedirs(destination_folder, exist_ok=True)

        for file in required_files:
            shutil.copy(os.path.join(folder, file), destination_folder)

        confout_gro = os.path.join(folder, "finalOutput", "confout.gro")
        if os.path.isfile(confout_gro):
            shutil.copy(confout_gro, destination_folder)

        for itp_file in os.listdir(folder):
            if itp_file.endswith(".itp"):
                shutil.copy(os.path.join(folder, itp_file), destination_folder)

        create_run_md_script(destination_folder)
        modify_simulation_time(destination_folder)
        modify_gen_seed(destination_folder)

def create_submit_script(destination_folder):
    """Create 'submit_md.sh' to submit all MD simulations."""
    submit_script_content = """#!/bin/bash

start_dir=$(pwd)

for dir in */ ; do
    cd "$dir"
    sbatch run_md.sh
    cd "$start_dir"
done
"""
    with open(os.path.join(destination_folder, "submit_md.sh"), "w") as submit_script_file:
        submit_script_file.write(submit_script_content)
    os.chmod(os.path.join(destination_folder, "submit_md.sh"), 0o755)

def create_run_md_script(destination_folder):
    """Create 'run_md.sh' to execute MD simulations."""
    cluster_config = {
        "CSB": f"""#!/bin/bash
#SBATCH -N 1
#SBATCH -n 32
#SBATCH -t {args.runtime}:00:00
#SBATCH --gpus-per-task=1
#SBATCH --job-name=md_simulation

module load gromacs
gmx grompp -f prod.mdp -c confout.gro -p topol.top -n index.ndx -o topol_prod.tpr --maxwarn 1
srun gmx mdrun -s topol_prod.tpr -o traj.trr -e ener.edr -c final.gro -g production.log -x traj_prod.xtc

mkdir -p finalOutput
echo -e "1 0" | gmx trjconv -pbc mol -s topol_prod.tpr -center -ur compact -f traj_prod.xtc -o traj_prod_pymol.xtc &>> visualization.log
""",
        "CESGA": f"""#!/bin/bash
#SBATCH -t {args.runtime}:00:00
#SBATCH --mem-per-cpu=4G
#SBATCH -N 1
#SBATCH -c 32
#SBATCH --gres=gpu:a100
#SBATCH --mail-type=begin
#SBATCH --mail-type=end
#SBATCH --mail-user=ruben.prieto@usc.es

module load gromacs
gmx grompp -f prod.mdp -c confout.gro -p topol.top -n index.ndx -o topol_prod.tpr --maxwarn 1
srun gmx_mpi mdrun -s topol_prod.tpr -o traj.trr -e ener.edr -c confout.gro -g production.log -x traj_prod.xtc
""",
        "TETRA": f"""#!/bin/bash
#SBATCH --job-name=md_simulation
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -c 16
#SBATCH --time=0-{args.runtime}:00:00
#SBATCH --mail-type=begin
#SBATCH --mail-type=end
#SBATCH --mail-user=ruben.prieto@usc.es

module load gromacs
gmx grompp -f prod.mdp -c confout.gro -p topol.top -n index.ndx -o topol_prod.tpr --maxwarn 1
srun gmx mdrun -s topol_prod.tpr -o traj.trr -e ener.edr -c final.gro -g production.log -x traj_prod.xtc
"""
    }
    run_md_script_content = cluster_config[args.cluster]
    with open(os.path.join(destination_folder, "run_md.sh"), "w") as run_md_script_file:
        run_md_script_file.write(run_md_script_content)
    os.chmod(os.path.join(destination_folder, "run_md.sh"), 0o755)

def modify_simulation_time(destination_folder):
    """Modify simulation time in 'prod.mdp'."""
    nsteps = args.simulation_time * 500000
    prod_mdp_path = os.path.join(destination_folder, "prod.mdp")
    with open(prod_mdp_path, "r") as file:
        lines = file.readlines()
    with open(prod_mdp_path, "w") as file:
        for line in lines:
            if line.strip().startswith("nsteps"):
                file.write(f"nsteps              =  {nsteps}   ; {args.simulation_time} ns\n")
            else:
                file.write(line)

def modify_gen_seed(destination_folder):
    """Set random gen_seed in 'prod.mdp'."""
    gen_seed = random.randint(1, 2147483647)
    prod_mdp_path = os.path.join(destination_folder, "prod.mdp")
    with open(prod_mdp_path, "r") as file:
        lines = file.readlines()
    with open(prod_mdp_path, "w") as file:
        for line in lines:
            if line.strip().startswith("gen_seed"):
                file.write(f"gen_seed            =  {gen_seed}\n")
            else:
                file.write(line)

def move_directories_to_pymemdyn(root_dir, exclude_dirs):
    """Move all directories except the excluded ones to 'pymemdyn'."""
    pymemdyn_folder = os.path.join(root_dir, "2.pymemdyn")
    os.makedirs(pymemdyn_folder, exist_ok=True)
    for item in os.listdir(root_dir):
        item_path = os.path.join(root_dir, item)
        if os.path.isdir(item_path) and item not in exclude_dirs:
            shutil.move(item_path, pymemdyn_folder)
    print(f"Directories moved to '{pymemdyn_folder}'.")

args = parse_arguments()
destination_folder = "3.md"
copy_files_in_directory(".", destination_folder)
move_directories_to_pymemdyn(".", [destination_folder, "1.input_files"])