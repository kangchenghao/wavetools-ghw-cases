# Native wavetools integration tests

The patch targets [wavetools main at `2a0bf2f`](https://github.com/hudson-trading/wavetools/tree/2a0bf2f868e02107d22753464e1d89b2cf21abde). Apply it from a clean checkout of that revision. It adds four tests to the existing Rust `diff_test` target, nine generated waveform files, the VHDL source, and a regeneration script. All checked-in waveforms use a 1 fs tick.

```sh
git apply --check /path/to/ghw-cross-format.patch
git apply /path/to/ghw-cross-format.patch
cargo test --test diff_test ghw_cross_format::
```

The active tests exercise VCD and FST with the current reader and check the record-path assertions against positive and negative examples. Two more are marked `#[ignore]` until a GHW reader is available. Run all four on a candidate implementation with this command:

```sh
cargo test --test diff_test ghw_cross_format:: -- --include-ignored
```

The GHW tests check a common marker in both comparison orders, the file that owns a missing record, a delayed edge, and a change visible only in the record. They allow an aggregate record or field paths in the diagnostic. The active control compares the marker inventory before trusting a filtered equality result. Once GHW is implemented and the tests pass, remove the two ignore attributes to run them by default.

Validation on Windows used the upstream v0.1.3 executables on files extracted from the patch. All 14 CLI invocations used by the active Rust control returned the expected results. Separate probes confirmed v0.1.3 rejects the GHW input (`wavediff` exit 2, `wavecat` exit 1). The patch applied cleanly and all nine files matched their sources byte-for-byte. The [Linux CI run](https://github.com/kangchenghao/wavetools-ghw-cases/actions/workflows/check.yml) builds the pinned upstream revision with the patch and executes the complete `diff_test` target, followed by the portable VCD/FST controls.
