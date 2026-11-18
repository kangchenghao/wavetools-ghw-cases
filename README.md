# Where did the VHDL record go?

These nine small waveforms reproduce a case from [wavetools #39](https://github.com/hudson-trading/wavetools/issues/39). GHDL writes a scalar and a two-field VHDL record to GHW. In the VCD from the **same simulation run**, only the scalar survives. Converting that VCD to FST preserves exactly what reached VCD. Other FST producers can represent different signal inventories.

A comparison of two files can therefore agree on every exported value while missing an actual change in the circuit.

## Run the controls

With Python 3.8+ and [wavediff](https://github.com/hudson-trading/wavetools/releases) on your path, run:

```sh
python run_cases.py
```

All inputs are included. You can also point to a binary with `--wavediff /path/to/wavediff`, or save the individual results with `--json results.json`.

**Observed with wavediff 0.1.3.** All 10 VCD/FST comparisons pass. The delayed marker is detected at 10 ns in both input orders. A change confined to the record leaves the VCD and VCD-derived FST identical as waveforms.

## Exercise a GHW reader

```sh
python run_cases.py --with-ghw --wavediff /path/to/candidate/wavediff
```

This adds 16 required comparisons. With v0.1.3 all 16 reach the binary and exit 2 because it cannot read GHW. The runner exits 1. The table describes the proposed behavior for a reader that supports the shared scalar and the record.

| What to compare | Expected observation |
| --- | --- |
| Full baseline GHW vs. baseline VCD or FST, in both orders | Exit 1 and list the record (or its fields) on the GHW side. |
| Only `*.marker` on those files | Exit 0. Moving its rising edge to 11 ns must give exit 1 and a first difference at 10 ns. This companion check catches a filter that accidentally selects nothing. |
| Baseline vs. record change, both GHW | The marker still agrees. The full comparison detects the changed record or flag at 10 ns. |

The cross-format checks use `--no-attrs` where native type metadata could differ. Every checked-in file uses a 1 fs time unit, so the first difference at 10 ns is tick 10,000,000. The suite tests digital values, names and physical times on this shared time base.

## Inspect or recreate the inputs

| Run | Scalar marker | Record valid | Record flag |
| --- | --- | --- | --- |
| baseline | High from 10 to 20 ns | High from 10 to 20 ns | Always low |
| delayed | High from 11 to 20 ns | High from 10 to 20 ns | Always low |
| record_change | High from 10 to 20 ns | High from 10 to 20 ns | High from 10 to 20 ns |

All signals start low. Read [the circuit](cross_format.vhd) or open [the baseline VCD](fixtures/baseline.vcd) and look for the GHDL comment about `packet`. For an independent check, run:

```sh
python verify_fixtures.py
python generate.py --output regenerated
python verify_fixtures.py --fixtures regenerated
```

Verification uses GHDL's `ghwdump` and GTKWave's `fst2vcd`. Regeneration uses `ghdl` and `vcd2fst`. Each script accepts explicit executable paths with the corresponding `--toolname` option. The nine shipped files and nine fresh outputs were independently checked with GHDL 6.0.0 and GTKWave 3.3.100 tools on Windows. Regenerated headers can contain a different date. The check compares signal declarations and transitions.

For an upstream checkout, a [self-contained Rust integration-test patch and its instructions](upstream/README.md) are included. The test cases are offered for coordination with the GHW reader author. [GHDL's waveform format notes](https://ghdl.github.io/ghdl/ghw/index.html) explain which information a VCD export can lose.

Maintained by kangchenghao. The fixture, automation and documentation were developed with AI assistance and checked against the named tools. To explore the example, change `marker_rise_ns` or a field assignment, regenerate into a separate directory, and inspect which comparison first reports a difference.
