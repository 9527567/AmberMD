from pathlib import Path
import os
from .equil import prep
import argparse
from . import pyamber
import logging
from logging import getLogger
import subprocess


def runCMD(inCmd, *, raise_on_fail: bool = True, logger: logging.Logger = getLogger("mmpbsa"), **kwargs):
    p = subprocess.Popen(
        inCmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = p.communicate()
    p.wait()
    if p.returncode == 0:
        status = 'Success'
    else:
        status = 'Fail'
        logger.error(f'{inCmd} run failed')
        logger.debug(f'stdout:\n{output}')
        logger.debug(f'stderr:\n{error}')
        if raise_on_fail:
            if kwargs.get('message', None) != None:
                raise RuntimeError(kwargs['message'])
            else:
                raise RuntimeError(f'{inCmd} run failed')
    return status, output, error


def split_pdb(pdb: str):
    try:
        import parmed as pd
        from pdb4amber.residue import (
            RESPROT, RESPROTE, RESNA,
            AMBER_SUPPORTED_RESNAMES,
            HEAVY_ATOM_DICT, RESSOLV)
    except:
        raise RuntimeError("you need to install parmed")
    com = pd.load_file(pdb)
    # remove water and ions
    water_mask = ':' + ','.join(RESSOLV)
    com.strip(water_mask)
    ns_names = list()
    for residue in com.residues:
        if len(residue.name) > 3:
            rname = residue.name[:3]
        else:
            rname = residue.name
        if rname.strip() not in AMBER_SUPPORTED_RESNAMES:
            logging.debug(f'ligand:{rname}')
            ns_names.append(rname)
            if len(ns_names) > 1:
                raise RuntimeError(
                    "Only a single ligand system is supported, or you can prepare your own system.")
    mol = com.copy(cls=pd.Structure)
    com.strip(f':{ns_names[0]}')
    com.write_pdb(f'pro.pdb')
    mol.strip(f"!:{ns_names[0]}")
    pd.formats.Mol2File.write(mol, "mol.mol2")
    return "pro.pdb", "mol.mol2"


def run_tleap(protein: str, mol: str,charge: int,multiplicity: int):
    cmdline = f'pdb4amber -i {protein} -o _{str(protein)} -y -d -p'
    runCMD(cmdline)
    protein_path = Path(protein).absolute()
    mol_path = Path(mol).absolute()
    cmdline = f'acpype -i {str(mol_path)} -c {charge} -m {multiplicity}'
    runCMD(cmdline, message="Perhaps you should check the charge of the ligand and the correctness of the hydrogen atom.")
    leapin = f"source leaprc.protein.ff14SB\n\
            source leaprc.DNA.OL15\n\
            source leaprc.RNA.OL3\n\
            source leaprc.water.tip3p\n\
            source leaprc.gaff2\n\
            pro = loadpdb _{protein}\n\
            loadamberparams {mol_path.stem}.acpype/{mol_path.stem}_AC.frcmod\n\
            mol = loadmol2 {mol_path.stem}.acpype/{mol_path.stem}_bcc_gaff2.mol2\n\
            com = combine{{pro mol}}\n\
            solvatebox com TIP3PBOX 10.0\n\
            addions2 com Na+ 0\n\
            addions2 com Cl- 0\n\
            saveamberparm com {protein_path.stem}_{mol_path.stem}.parm7 {protein_path.stem}_{mol_path.stem}.rst7\n\
            quit"
    with open("leap.in", "w") as f:
        for i in leapin:
            f.write(i)
    runCMD('tleap -f leap.in')
    return f'{protein_path.stem}_{mol_path.stem}.parm7', f'{protein_path.stem}_{mol_path.stem}.rst7'


def mmpbsa(parm7: str, rst7: str, netcdf: str, system: pyamber.SystemInfo):
    parm7 = Path(parm7).absolute()
    rst7 = Path(rst7).absolute()

    try:
        import parmed
    except:
        raise RuntimeError("you need to install parmed")
    amber_top = parmed.load_file(str(parm7), str(rst7))
    if not parm7.with_suffix(".top").is_file():
        amber_top.save(str(parm7.with_suffix(".top")))
    cpptraj_in = f'parm {str(parm7)}\n \
trajin {str(rst7)}\n \
trajout {str(parm7.with_suffix(".pdb"))}\n \
go\n \
trajin {netcdf}\n \
unwrap :1-{system.getNprotein()}\n \
center :1-{system.getNprotein()} mass origin\n \
image center origin familiar\n \
trajout {str(parm7.with_suffix(".xtc"))}\n \
go\n \
exit '
    with open("cpptraj.in", "w") as f:
        for i in cpptraj_in:
            f.write(i)
    runCMD(f'cpptraj -i cpptraj.in')
    if not Path("MMPBSA").is_dir():
        Path("MMPBSA").mkdir()
    os.chdir("MMPBSA")
    from multiprocessing import cpu_count
    make_ndx = f"echo q | gmx make_ndx -f {str(parm7.with_suffix('.pdb'))} -o index.ndx"
    runCMD(make_ndx)
    mmpbsa_in = f'&general\n \
startframe=1, endframe=99999, verbose=2,interval=1,\n \
/\n \
&gb\n \
igb=5,\n \
/\n \
&pb\n \
istrng=0.1500,inp=1,radiopt = 0\n \
/\n    \
&decomp\n \
idecomp=2, dec_verbose=3,\n \
print_res="within 4"\n \
/'
    with open("mmpbsa.in", 'w') as f:
        for i in mmpbsa_in:
            f.write(i)
    mmpbsa = f"mpirun -np {cpu_count() // 2} gmx_MMPBSA MPI -O -i mmpbsa.in -cs {str(parm7.with_suffix('.pdb'))} -ci index.ndx -cg 1 13 -ct {str(parm7.with_suffix('.xtc'))}  -cp \
    {str(parm7.with_suffix('.top'))} -nogui"
    runCMD(mmpbsa)


def arg_parse():
    parser = argparse.ArgumentParser(description='Demo of MMPBSA')
    parser.add_argument('--protein', '-p', type=str,
                        required=True, help="pdb file for protein")
    parser.add_argument('--mol2', '-m', type=str,
                        required=False, help='mol2 file for mol')
    parser.add_argument('--temp', '-t', type=float,
                        required=False, help='Temperature', default=303.15)
    parser.add_argument("--ns", '-n', type=int,
                        help="time for MD(ns)", default=100)
    parser.add_argument("--charge", type=int,
                        default=0, help="charge of mol")
    parser.add_argument("--multiplicity",type=int,
                        default=1,help="multiplicity of mol")
    args = parser.parse_args()
    return args


def mmpbsa():
    args = arg_parse()
    protein = args.protein
    mol = args.mol2
    temp = args.temp
    if mol is None:
        protein, mol = split_pdb(protein)
    parm7, rst7 = run_tleap(protein, mol, args.charge, args.multiplicity)
    s = pyamber.SystemInfo(parm7, rst7)
    heavymask = "\"" + s.getHeavyMask() + "\""
    backbonemask = "\"" + s.getBackBoneMask() + "\""
    rst7 = prep(rst7=rst7, s=s, temp=temp, heavymask=heavymask,
                backbonemask=backbonemask, loop=20)
    md = pyamber.NPT("md", s, rst7, rst7, ntwx=50000,
                     irest=True, nscm=1000, nstlim=args.ns * 500000)
    md.Run()
    mmpbsa(parm7, rst7, "md.nc", s)


if __name__ == '__main__':
    mmpbsa()
