
# Molecular Dynamics and FEP Setup

This repository contains scripts for setting up and running molecular dynamics (MD) simulations and free energy perturbation (FEP) calculations using GROMACS and related tools.

## Prerequisites

Before using these scripts, ensure you have the following software installed:
- **Python** (3.7 or higher). Recommended to create a Conda environment:
  ```bash
  conda create -n py37 python=3.7
  conda activate py37
  ```
- **PyModSim**: Install via [GitHub](https://github.com/GPCR-ModSim/pymodsim).
- **PyMemDyn**: Install via [GitHub](https://github.com/GPCR-ModSim/pymemdyn).
- **LigParGen**: Install via [GitHub](https://github.com/Isra3l/ligpargen).
- **GROMACS**: Required for MD simulations.
- **Schrödinger Maestro** (or equivalent software) for protein and ligand preparation.

## Workflow Overview

### Step 1: Align Complex with PyModSim

Before proceeding with the provided scripts, the **PyModSim** tool must be used to align the protein-ligand complex with the membrane. This step ensures that the system is properly oriented for subsequent docking and molecular dynamics simulations.

#### Instructions for PyModSim Execution

1. **Prepare Input Files**:
   - Export the protein and ligand from Schrödinger Maestro (or other software) as separate PDB files.

2. **Run PyModSim**:
   ```bash
   pymodsim -n 3 -p unaligned_protein.pdb
   ```
   Replace `unaligned_protein.pdb` with the name of your protein file.

3. **Output**:
   PyModSim generates a properly aligned protein file in `finalOutput/homology.pdb` that can be used as input for the next steps.

> **Note**: Ensure the complex is visually inspected after alignment to confirm correctness.

---

### Step 2: Ligand Modelling or Docking
This protocol was tested by using **Schrödinger Maestro**. After docking, export protein and ligands as separated pdb files.

### Step 3: Prepare System for PyMemDyn

Use the `setup_pym.py` script to prepare ligand-receptor systems for PyMemDyn simulations.

#### Usage

```bash
python setup_pym.py [--noclean] [-C CLUSTER] [-p PROTEIN]
                    [-l LIGAND] [-w WATERS] [-i IONS]
                    [-r RESTRAINT] [--fep]
```

| Argument       | Description                                                                                                                                                        |
|----------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `--noclean`    | Retain intermediate files.                                                                                                                                        |
| `-C CLUSTER`   | Specify the cluster for job submission (CSB, CESGA, TETRA).                                                                                                       |
| `-p PROTEIN`   | Protein PDB file (default: `protein.pdb`).                                                                                                                        |
| `-l LIGAND`    | Ligand identifier in the PDB (default: `LIG`).                                                                                                                    |
| `-w WATERS`    | Crystallized water identifiers (default: `HOH`).                                                                                                                  |
| `-i IONS`      | Crystallized ion identifiers (default: `NA`).                                                                                                                     |
| `-r RESTRAINT` | Restraint type: `bw` (Ballesteros-Weinstein) or `ca` (C-alpha). Default: `ca`.                                                                                     |
| `--fep`        | Prepare files for FEP calculations (adds `--full_relax false` to PyMemDyn execution).                                                                              |

The script:
1. Creates a folder for each ligand.
2. Generates the ligand-receptor complex.
3. Runs LigParGen for ligand parameterization.
4. Prepares SLURM scripts (`pymemdyn.sh` for PyMemDyn execution and `submit_pym.sh` for batch submission).

**Input Structure**:
```bash
my_project/
├── protein.pdb
├── ligand1.pdb
├── ligand2.pdb
```

**Output Structure**:
```bash
my_project/
├── 1.input_files/
│   ├── protein.pdb
│   ├── ligand1.pdb
│   ├── ligand2.pdb
├── ligand1/
│   ├── complex.pdb
│   ├── LIG.gro
│   ├── LIG.itp
│   └── pymemdyn.sh
├── ligand2/
├── submit_pym.sh
```

Submit PyMemDyn jobs:
```bash
sh submit_pym.sh
```

---

### Step 3: Setup MD Simulations

After PyMemDyn equilibration, use the `setup_md.py` script to prepare MD simulation files.

#### Usage

```bash
python setup_md.py [-t TIME] [-rt RUNTIME] [-C CLUSTER] [-n NUM_REPLICAS]
```

| Argument         | Description                                                                                             |
|------------------|---------------------------------------------------------------------------------------------------------|
| `-t TIME`        | Simulation time in nanoseconds (default: 25).                                                           |
| `-rt RUNTIME`    | Runtime limit in hours (default: 36).                                                                   |
| `-C CLUSTER`     | Cluster for job submission (CSB, CESGA, TETRA).                                                         |
| `-n NUM_REPLICAS`| Number of replicas for MD simulations (default: 3).                                                     |

The script:
1. Copies required files to a `3.md/` directory.
2. Prepares SLURM scripts for MD simulations (`run_md.sh` for each replica and `submit_md.sh` for batch submission).
3. Modifies `prod.mdp` to set the simulation time and random seed.

**Input Structure**:
```bash
my_project/
├── 1.input_files/
│   ├── protein.pdb
│   ├── ligand1.pdb
│   ├── ligand2.pdb
├── ligand1/
│   ├── complex.pdb
│   ├── LIG.gro
│   ├── LIG.itp
│   └── pymemdyn.sh
├── ligand2/
├── submit_pym.sh
```


**Output Structure**:
```bash
my_project/
├── 1.input_files/
│   ├── protein.pdb
│   ├── ligand1.pdb
│   ├── ligand2.pdb
├── 2.pymemdyn/
│   ├── ligand1/
│   ├── ligand2/
├── 3.md/
│   ├── lig1_1 <- Replica 1 ligand 1
│   │   ├── LIG.itp         
│   │   ├── ffoplsaa_mod.itp
│   │   ├── index.ndx  
│   │   ├── posre.itp      
│   │   ├── posre_NA.itp  
│   │   ├── run_md.sh <- SLURM execution for MD
│   │   ├── topol.tpr
│   │   ├── LIG_backup.itp  
│   │   ├── ffoplsaabon_mod.itp  
│   │   ├── ions.itp   
│   │   ├── posre_HOH.itp
│   │   ├── prod.mdp <- Modified with setup_md.py
│   │   ├── spc.itp
│   │   ├── confout.gro
│   │   ├── ffoplsaanb_mod.itp
│   │   ├── popc.itp
│   │   ├── posre_LIG.itp
│   │   ├── protein.itp
│   │   ├── topol.top
│   ├── lig1_2 <- Replica 2 ligand 1
│   ├── lig1_n <- Replica n ligand 1
│   └── submit_md.sh <- Calls run_md.sh inside each directory

```

---

## License

---

## Acknowledgments

- [PyMemDyn](https://github.com/GPCR-ModSim/pymemdyn)
- [PyModSim](https://github.com/GPCR-ModSim/pymodsim)
- [LigParGen](https://github.com/Isra3l/ligpargen)

For issues or contributions, contact [ruben.prieto@usc.es](mailto:ruben.prieto@usc.es).
