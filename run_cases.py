"""Exercise the wavediff CLI against the adjacent cross-format fixtures."""

import argparse
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


MARKER_FILTER = ("--no-attrs", "--filter", "*.marker")
TICK_10_NS = 10_000_000  # All three formats use a 1 fs time unit.


@dataclass(frozen=True)
class Case:
    left: str
    right: str
    expectation: str
    options: tuple = ()


def both_orders(left, right, expectation, options=()):
    yield Case(left, right, expectation, options)
    yield Case(right, left, expectation, options)


def controls():
    yield from both_orders("baseline.vcd", "baseline.fst", "equal")
    yield from both_orders("baseline.vcd", "baseline.fst", "equal", MARKER_FILTER)
    yield from both_orders("baseline.vcd", "delayed.fst", "marker-edge", MARKER_FILTER)
    yield from both_orders("baseline.vcd", "record_change.fst", "equal")
    yield from both_orders("baseline.fst", "record_change.vcd", "equal")


def ghw_cases():
    for suffix in ("vcd", "fst"):
        projected = f"baseline.{suffix}"
        yield from both_orders("baseline.ghw", projected, "packet-only-in-ghw", ("--no-attrs",))
        yield from both_orders("baseline.ghw", projected, "equal", MARKER_FILTER)
        yield from both_orders("delayed.ghw", projected, "marker-edge", MARKER_FILTER)
    yield from both_orders("baseline.ghw", "record_change.ghw", "equal", MARKER_FILTER)
    yield from both_orders("baseline.ghw", "record_change.ghw", "packet-edge", ("--no-attrs",))


def signal_parts(name):
    # Readers can expose a record as an aggregate or as separate field paths.
    return re.findall(r"[A-Za-z0-9_]+", name.lower())


def is_fixture_signal(name, candidates):
    parts = signal_parts(name)
    return any(parts[-len(candidate):] == candidate for candidate in candidates)


def packet_owner(output, ghw_file):
    """Read the per-file signal inventory, ignoring unrelated diagnostics and value rows."""
    owner = None
    fields = {"valid", "flag"}
    covered = set()
    for line in output.splitlines():
        section = re.fullmatch(r"\s*Only in (.+):\s*", line)
        if section:
            owner = section[1]
        elif line.startswith("    ") and owner:
            if owner != ghw_file:
                return False
            parts = signal_parts(line)
            if parts[-2:] == ["cross_format", "packet"]:
                covered.update(fields)
            elif parts[-3:-1] == ["cross_format", "packet"] and parts[-1] in fields:
                covered.add(parts[-1])
            else:
                return False
        else:
            owner = None
    return covered == fields


def first_edge(output, expectation):
    # wavediff emits a row as '<tick> <signal> <difference>'. A missing name
    # can also emit time rows; it must not satisfy a value-change test.
    if "Signal name mismatch:" in output:
        return False
    candidates = [["cross_format", "marker"]] if expectation == "marker-edge" else [
        ["cross_format", "packet"], ["cross_format", "packet", "flag"]
    ]
    ticks = []
    for line in output.splitlines():
        row = re.fullmatch(r"\s*(\d+)\s+(\S+)\s+(.+)", line)
        if row:
            if not is_fixture_signal(row[2], candidates):
                return False
            if not re.search(r"!=|missing time in file|only in file", row[3]):
                return False
            ticks.append(int(row[1]))
    return bool(ticks) and min(ticks) == TICK_10_NS


def run(case, binary, directory):
    args = [*case.options, case.left, case.right]
    expected = 0 if case.expectation == "equal" else 1
    try:
        proc = subprocess.run(
            [binary, *args], cwd=directory, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return dict(args=args, expectation=case.expectation, expected_exit=expected,
                    actual_exit=None, passed=False, detail=str(error))

    output = "\n".join(s.strip() for s in (proc.stderr, proc.stdout) if s.strip())
    fatal = re.search(r"^\s*(error:|fatal:|thread .* panicked)", output, re.I | re.M)
    passed = proc.returncode == expected and not fatal
    if passed and case.expectation == "packet-only-in-ghw":
        ghw_file = case.left if case.left.endswith(".ghw") else case.right
        passed = packet_owner(output, ghw_file)
    elif passed and case.expectation in ("marker-edge", "packet-edge"):
        passed = first_edge(output, case.expectation)
    return dict(args=args, expectation=case.expectation, expected_exit=expected,
                actual_exit=proc.returncode, passed=passed, detail=output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wavediff", default="wavediff", help="binary path or command on PATH")
    parser.add_argument("--fixtures", type=Path, default=Path(__file__).with_name("fixtures"))
    parser.add_argument("--with-ghw", action="store_true", help="also require the GHW reader cases to pass")
    parser.add_argument("--json", type=Path, help="save individual comparisons and diagnostics")
    args = parser.parse_args()
    binary = shutil.which(args.wavediff)
    if not binary:
        parser.error(f"cannot find executable {args.wavediff!r}")
    binary = str(Path(binary).resolve())
    cases = list(controls())
    if args.with_ghw:
        cases.extend(ghw_cases())
    inputs = {name for case in cases for name in (case.left, case.right)}
    for name in sorted(inputs):
        if not (args.fixtures / name).is_file():
            parser.error(f"missing fixture {args.fixtures / name}")
    results = []
    for case in cases:
        result = run(case, binary, args.fixtures)
        results.append(result)
        status = "PASS" if result["passed"] else "FAIL"
        print(f"{status} {case.expectation} | {' '.join(result['args'])} | exit {result['actual_exit']}")
        if not result["passed"]:
            print(result["detail"] or "(no diagnostic)")
    passed = sum(row["passed"] for row in results)
    print(f"{passed}/{len(results)} passed")
    if args.json:
        args.json.write_text(json.dumps({"with_ghw": args.with_ghw, "results": results},
                                        indent=2) + "\n", encoding="utf-8")
    return int(passed != len(results))


if __name__ == "__main__":
    raise SystemExit(main())
