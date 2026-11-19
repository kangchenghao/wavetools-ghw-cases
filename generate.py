"""Regenerate the GHW, VCD, VCD-derived FST and native FST fixtures."""

import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parent
CASES = {
    "baseline": (),
    "delayed": ("-gmarker_rise_ns=11",),
    "record_change": ("-gtoggle_flag=true",),
}


def tool_path(command):
    resolved = shutil.which(command)
    if resolved is None:
        raise SystemExit(f"Executable could not be found: {command}")
    return str(Path(resolved).resolve())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ghdl", default="ghdl")
    parser.add_argument("--vcd2fst", default="vcd2fst")
    parser.add_argument("--output", type=Path, default=ROOT / "fixtures")
    args = parser.parse_args()
    ghdl, converter = tool_path(args.ghdl), tool_path(args.vcd2fst)

    with tempfile.TemporaryDirectory() as scratch:
        work = Path(scratch)
        shutil.copyfile(ROOT / "cross_format.vhd", work / "cross_format.vhd")
        subprocess.run([ghdl, "-a", "--std=08", "cross_format.vhd"], cwd=work, check=True)
        subprocess.run([ghdl, "-e", "--std=08", "cross_format"], cwd=work, check=True)
        files = []
        for name, generics in CASES.items():
            vcd, ghw, fst = (f"{name}.{ext}" for ext in ("vcd", "ghw", "fst"))
            native_fst = f"{name}.native.fst"
            simulate = [ghdl, "-r", "--std=08", "cross_format", *generics]
            subprocess.run(
                [*simulate, f"--wave={ghw}", f"--vcd={vcd}"],
                cwd=work,
                check=True,
            )
            subprocess.run([converter, vcd, fst], cwd=work, check=True)
            # A separate run with identical stimulus exercises GHDL's own FST writer.
            subprocess.run([*simulate, f"--fst={native_fst}"], cwd=work, check=True)
            files.extend((ghw, vcd, fst, native_fst))

        for name in files:
            if not (work / name).stat().st_size:
                raise SystemExit(f"Empty fixture: {name}")
        args.output.mkdir(parents=True, exist_ok=True)
        for name in files:
            shutil.copyfile(work / name, args.output / name)
    print(f"Generated {len(files)} fixtures in {args.output}")


if __name__ == "__main__":
    main()
