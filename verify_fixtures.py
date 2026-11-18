"""Check the small checked-in traces independently of wavediff."""

import argparse
import re
import subprocess
from pathlib import Path


NS = 1_000_000  # physical timestamps below are in femtoseconds
TOP = "cross_format"
MARKER = f"{TOP}/marker"
PACKET = f"{TOP}/packet"
FS_PER_UNIT = {"fs": 1, "ps": 1_000, "ns": NS, "us": 10**9, "ms": 10**12, "s": 10**15}


def expect(label, actual, expected):
    if actual != expected:
        raise ValueError(f"{label}: expected {expected!r}, found {actual!r}")


def output(tool, *args):
    result = subprocess.run([tool, *args], capture_output=True, text=True, errors="replace")
    if result.returncode:
        raise ValueError(f"{tool} exited {result.returncode}: {result.stderr.strip()}")
    return result.stdout


def record_change(trace, time, value):
    if not trace or trace[-1][1] != value:
        trace.append((time, value))


def read_vcd(text):
    # Only the scalar form used by the fixtures is needed. Declarations are
    # collected across all scopes, so a packet that was flattened is visible.
    header, body = re.split(r"\$enddefinitions\s+\$end", text, maxsplit=1)
    scopes = []
    ids = {}
    for match in re.finditer(r"\$(\w+)\s+(.*?)\s*\$end\b", header, re.DOTALL):
        command, content = match.group(1), match.group(2).strip()
        words = content.split()
        if command == "scope":
            scopes.append(words[1])
        elif command == "upscope":
            scopes.pop()
        elif command == "var":
            name = "/".join([*scopes, words[3]])
            if name in ids:
                raise ValueError(f"duplicate VCD declaration {name}")
            ids[name] = (words[1], words[2])
    expect("VCD declared signals", sorted(ids), [MARKER])
    expect("VCD marker width", ids[MARKER][0], "1")
    expect("VCD unclosed scopes", scopes, [])
    scale = re.search(r"\$timescale\s+(\d+)\s*(fs|ps|ns|us|ms|s)\s*\$end", header)
    if not scale:
        raise ValueError("missing or unsupported VCD timescale")
    tick = int(scale[1]) * FS_PER_UNIT[scale[2]]
    trace = []
    time = 0
    for raw in body.splitlines():
        line = raw.strip()
        if line.startswith("#"):
            time = int(line[1:]) * tick
        elif line and line[0].lower() in "01xz" and line[1:] == ids[MARKER][1]:
            record_change(trace, time, line[0].lower())
    return trace


def read_ghw(text):
    # GHDL lists the leaves of each record in its declaration order and
    # identifies their contiguous scalar IDs in the hierarchy.
    signals = dict(re.findall(r"^signal /([^:]+): (.+)$", text, re.MULTILINE))
    expect("GHW declared signals", sorted(signals), sorted([MARKER, PACKET]))
    marker = re.fullmatch(r"bit: #(\d+)", signals[MARKER])
    packet = re.fullmatch(r"(\w+): #(\d+)-#(\d+)", signals[PACKET])
    if not marker or not packet:
        raise ValueError(f"unexpected GHW declarations {signals!r}")
    fields = re.search(rf"^type {re.escape(packet[1])} is record\n(.*?)^end record;", text, re.M | re.S)
    if not fields:
        raise ValueError(f"missing record definition for {packet[1]}")
    expect("GHW packet fields", fields[1].split(), ["valid:", "bit;", "flag:", "bit;"])
    first, last = int(packet[2]), int(packet[3])
    expect("GHW packet width", last - first + 1, 2)
    names = {int(marker[1]): "marker", first: "valid", last: "flag"}
    expect("GHW distinct scalar IDs", len(names), 3)
    traces = {name: [] for name in names.values()}
    time = None
    for line in text.splitlines():
        stamp = re.fullmatch(r"Time is (\d+) fs", line)
        value = re.fullmatch(r"#(\d+): '([^']+)' \(\d+\)", line)
        if stamp:
            time = int(stamp[1])
        elif value and int(value[1]) in names:
            if time is None:
                raise ValueError("GHW sample has no timestamp")
            record_change(traces[names[int(value[1])]], time, value[2])
    return traces


def verify(args):
    for case in ("baseline", "delayed", "record_change"):
        rise = 11 if case == "delayed" else 10
        pulse = [(0, "0"), (10 * NS, "1"), (20 * NS, "0")]
        marker = [(0, "0"), (rise * NS, "1"), (20 * NS, "0")]
        for extension in ("ghw", "vcd", "fst"):
            path = args.fixtures / f"{case}.{extension}"
            try:
                if extension == "ghw":
                    actual = read_ghw(output(args.ghwdump, "-t", "-H", "-s", path))
                    expect("marker", actual["marker"], marker)
                    expect("packet.valid", actual["valid"], pulse)
                    expect("packet.flag", actual["flag"], pulse if case == "record_change" else [(0, "0")])
                else:
                    text = path.read_text(encoding="ascii") if extension == "vcd" else output(args.fst2vcd, path)
                    expect("marker", read_vcd(text), marker)
            except (OSError, ValueError, IndexError) as exc:
                raise ValueError(f"{path}: {exc}") from exc
            print(f"PASS {path.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ghwdump", default="ghwdump")
    parser.add_argument("--fst2vcd", default="fst2vcd")
    parser.add_argument("--fixtures", type=Path, default=Path(__file__).resolve().parent / "fixtures")
    try:
        verify(parser.parse_args())
    except ValueError as exc:
        parser.exit(1, f"FAIL {exc}\n")
