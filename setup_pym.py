import os
import argparse
import shutil

def parse_arguments():
    parser = argparse.ArgumentParser(description="Process ligand and protein for PyMemDyn execution.")
    parser.add_argument("--noclean", action="store_true", help="Do not clean the directory after processing.")
    parser.add_argument("-C", "--cluster", choices=["CSB", "CESGA", "TETRA"], default="TETRA", help="Choose the cluster (default: TETRA).")
    parser.add_argument("-p", "--protein", nargs="?", default="protein.pdb", help="Protein file name (default: protein.pdb).")
    parser.add_argument("-l", nargs="?", default="LIG", help="Ligand identifier in provided PDB (default: LIG).")

    # Parameters for PyMemDyn execution
    parser.add_argument("-r", "--res", nargs="?", default="ca", help="Restraints (default: ca). Options: bw (Ballesteros-Weinstein Restrained Relaxation), ca (C-Alpha Restrained Relaxation).")
    parser.add_argument("-w", nargs="?", default="HOH", help="Water identifiers (default: HOH).")
    parser.add_argument("-i", nargs="?", default="NA", help="Ion identifiers (default: NA).")
    parser.add_argument("-fep", "--fep", action="store_true", help="Prepare files for FEP calculations (add --full_relax false to PyMemDyn script).")
    return parser.parse_args()

args = parse_arguments()
start_dir = os.getcwd()
if args.cluster:
    print(f"Selected cluster: {args.cluster}.")

# Cuenta el número de archivos .pdb que serán procesados
pdb_files = [file for file in os.listdir(".") if file.endswith(".pdb") and file != args.protein]
total_files = len(pdb_files)

# Loop a través de los .pdb
for idx, file in enumerate(pdb_files, start=1):
    dir_name = os.path.splitext(file)[0]
    print(f"Processing ({idx}/{total_files}): {dir_name}")  # Muestra progreso

    # Leer el contenido del archivo, eliminar líneas innecesarias y reemplazar identificadores
    with open(file, "r") as f:
        content = f.readlines()
    content = [line for line in content if not line.startswith(("END", "CONECT", "REMARK", "TITLE"))]
    content = [line.replace(args.l, "LIG") for line in content]

    # Crear un directorio para el ligando y guardar el archivo modificado
    os.makedirs(dir_name, exist_ok=True)
    ligand_path = os.path.join(dir_name, "LIG.pdb")
    with open(ligand_path, "w") as f:
        f.writelines(content)

    # Concatenar el archivo de proteína y el ligando para crear complex.pdb
    protein_path = args.protein
    complex_path = os.path.join(dir_name, "complex.pdb")
    with open(protein_path, "r") as f_protein, open(ligand_path, "r") as f_ligand, open(complex_path, "w") as f_complex:
        f_complex.write(f_protein.read())
        f_complex.write(f_ligand.read())

    # Cambiar al directorio del ligando
    os.chdir(dir_name)

    # Ejecutar LigParGen y renombrar archivos
    os.system(f"ligpargen -i LIG.pdb -cb 0 -ob 3 -r LIG -n LIG > ligpargen.log 2>&1")
    os.rename("LIG.gmx.gro", "LIG.gro")
    os.rename("LIG.openmm.pdb", "LIG.pdb")
    os.rename("LIG.gmx.itp", "LIG.itp")

    # Crear el script pymemdyn.sh dentro del directorio
    pymemdyn_content = ""
    if args.cluster == "CSB":
        pymemdyn_content = f"""#!/bin/bash -l
#SBATCH -N 1
#SBATCH -n 32
#SBATCH -t 24:00:00
#SBATCH --gpus-per-task=1
#SBATCH --job-name=pymemdyn
pymemdyn -p complex.pdb --res {args.res} -w {args.w} -i {args.i} -l LIG {"--full_relax false" if args.fep else ""}\n"""
    elif args.cluster == "CESGA":
        pymemdyn_content = f"""#!/bin/bash -l
#SBATCH -N 1
#SBATCH -c 32
#SBATCH --mem-per-cpu=4G
#SBATCH -t 24:00:00
#SBATCH --job-name=pymemdyn
#SBATCH --mail-type=begin
#SBATCH --mail-type=end
#SBATCH --mail-user=ruben.prieto+slurm@usc.es
pymemdyn -p complex.pdb --res {args.res} -w {args.w} -i {args.i} -l LIG {"--full_relax false" if args.fep else ""}\n"""
    elif args.cluster == "TETRA":
        pymemdyn_content = f"""#!/bin/bash -l
#SBATCH -N 1
#SBATCH -n 32
#SBATCH -t 24:00:00
#SBATCH --job-name=pymemdyn
#SBATCH --mail-type=begin
#SBATCH --mail-type=end
#SBATCH --mail-user=ruben.prieto+slurm@usc.es
pymemdyn -p complex.pdb --res {args.res} -w {args.w} -i {args.i} -l LIG {"--full_relax false" if args.fep else ""}\n"""

    with open("pymemdyn.sh", "w") as f_pymemdyn:
        f_pymemdyn.write(pymemdyn_content)
    os.chdir(start_dir)

    print(f"Processing of {dir_name} complete. Remaining: {total_files - idx}")

# Hacer una copia de seguridad de los archivos .pdb proporcionados
os.makedirs("inputFiles", exist_ok=True)
os.system("mv *.pdb inputFiles/")

# Crear el script submit_pym.sh
with open("submit_pym.sh", "w") as f_submit:
    f_submit.write("#!/bin/bash\n\n")
    f_submit.write("echo 'Processing directories:'\n")
    f_submit.write("start_dir=$(pwd)\n")
    f_submit.write("for folder in ./*; do\n")
    f_submit.write("    if [ -d \"$folder\" ]; then\n")
    f_submit.write("        cd \"$folder\" || continue\n")
    f_submit.write("        sbatch pymemdyn.sh\n")
    f_submit.write("        cd \"$start_dir\"\n")
    f_submit.write("    fi\n")
    f_submit.write("done\n")
    f_submit.write("echo 'All jobs submitted.'\n")
print("All ligands processed. Provided PDB files were moved to inputFiles directory.")