# Native wavetools integration tests

The patch targets [wavetools main at `2a0bf2f`](https://github.com/hudson-trading/wavetools/tree/2a0bf2f868e02107d22753464e1d89b2cf21abde). Apply it from a clean checkout of that revision. It adds six tests to the Rust `diff_test` target, twelve small waveforms, the VHDL source, and a regeneration script. Every waveform uses a 1 fs tick.

```sh
git apply --check /path/to/ghw-cross-format.patch
git apply /path/to/ghw-cross-format.patch
cargo test --locked --test diff_test ghw_cross_format::
```

Three tests run on the existing readers. They check scalar timing, field-path diagnostics and the difference between two FST export paths. GHDL 6.0.0 writes `packet.valid` and `packet.flag` when given `--fst`. Converting its VCD export to FST produces a trace containing only `marker`. The native FST control detects a flag-only change at 10 ns. The remaining three tests use GHW inputs. Run all six against a candidate reader with:

```sh
cargo test --locked --test diff_test ghw_cross_format:: -- --include-ignored
```

The GHW tests distinguish two behaviors. Against VCD or VCD-derived FST, the full comparison should report a record on the GHW side. Its diagnostic can name the aggregate or both fields. Against native FST, the proposed interoperability test uses the same flattened field paths that `wavecat --names` prints for native FST, including `cross_format.packet.flag`. It checks equality and a deliberate field-only change in both format orders. Each filtered comparison first verifies that the selected signal exists in both inputs. GHW readers that expose only an aggregate would need a field mapping to pass that interoperability test.

On Windows, the upstream v0.1.3 executables gave the expected results on all 28 CLI invocations in the active Rust controls. The patch applied to the pinned revision, and its twelve waveform files matched the checked-in inputs byte-for-byte. The [Linux workflow](https://github.com/kangchenghao/wavetools-ghw-cases/actions/workflows/check.yml) builds the pinned revision with the patch and runs the full `diff_test` target followed by the portable controls.
