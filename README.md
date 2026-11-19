# Where did the VHDL record go?

GHDL 6.0.0 can write both fields of a VHDL record to FST. The route to the file matters. With the same circuit and stimulus, these are the signal inventories we observed:

| File in `fixtures/` | How it was made | Signals present in this circuit |
| --- | --- | --- |
| `*.ghw` | GHDL `--wave` | `marker` and both fields of `packet` |
| `*.native.fst` | GHDL `--fst`, in a separate simulation with identical generics | `marker`, `packet.valid`, `packet.flag` |
| `*.vcd` | GHDL `--vcd`, emitted alongside GHW | `marker` only |
| `baseline.fst`, `delayed.fst`, `record_change.fst` | GTKWave `vcd2fst` on those VCDs | `marker` only |

The [discussion in wavetools #39](https://github.com/hudson-trading/wavetools/issues/39#issuecomment-6989747366) prompted the direct FST control. The GHDL VCD export omits the record. The proposed wavetools tests check how a GHW reader compares values that **are present** and reports signals present on only one side.

## Run the controls

With Python 3.8+ and [wavediff](https://github.com/hudson-trading/wavetools/releases) on your path, run:

```sh
python run_cases.py
```

All inputs are included. The 22 VCD/FST controls passed with wavediff 0.1.3. You can point to another binary with `--wavediff /path/to/wavediff`, or save individual results with `--json results.json`.

**Try the record-only change with wavediff 0.1.3.** The first command below reports the flag at tick 10,000,000 (10 ns) and exits 1. The second exits 0. GHDL had already dropped the flag when it wrote the VCDs used for the second pair.

```sh
wavediff --no-attrs fixtures/baseline.native.fst fixtures/record_change.native.fst
wavediff --no-attrs fixtures/baseline.fst fixtures/record_change.fst
```

## Exercise a GHW reader

```sh
python run_cases.py --with-ghw --wavediff /path/to/candidate/wavediff
```

This adds 24 required GHW comparisons. On v0.1.3, each GHW comparison reaches the binary and returns exit 2 because the reader is unavailable. The runner marks those comparisons as failures. The table describes the proposed behavior for a reader that exposes the shared record fields.

| What to compare | Expected observation |
| --- | --- |
| Baseline GHW vs. native FST | Corresponding fields agree. Comparing against the recording with only the flag changed must identify a difference at 10 ns. |
| Full baseline GHW vs. baseline VCD or VCD-derived FST, in both orders | Exit 1 and list the record (or its fields) on the GHW side. |
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

Verification uses GHDL's `ghwdump` and GTKWave's `fst2vcd` to inspect the declared signals and transitions independently of wavediff. Regeneration uses `ghdl` and `vcd2fst`. Each script accepts explicit executable paths with the corresponding `--toolname` option. The checked-in set covers three stimuli and four export routes. Regenerated headers can contain a different date.

For an upstream checkout, a [self-contained Rust integration-test patch and its instructions](upstream/README.md) are included. The test cases are offered for coordination with the GHW reader author. [GHDL's waveform format notes](https://ghdl.github.io/ghdl/ghw/index.html) explain which information a VCD export can lose.

Maintained by kangchenghao. The fixture, automation and documentation were developed with AI assistance and checked against the named tools. To explore the example, change `marker_rise_ns` or a field assignment, regenerate into a separate directory, and inspect which comparison first reports a difference.
