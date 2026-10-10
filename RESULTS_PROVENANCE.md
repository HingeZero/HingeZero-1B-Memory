# Data provenance and boundaries

The original executed one-billion-pattern results are preserved in `billion_results.csv`, the accompanying C++20 report and the sealed protocol. The original run captured 12 queries across two targets, 8 correct IDs, and 12 successful exact tagged-state witnesses.

`verify_recorded_results.py` checks the internal counts and consistency of the included CSV, not an independent reproduction.

`run_smoke.sh` performs a small fresh native run and tests preservation, witness and two retrieval conditions. `run_1b.sh` regenerates the full billion-pattern workload; it needs ~16 GB free disk space and sufficient time.

The witness property proves selected state membership and integrity, not that a corrupted cue must retrieve the intended memory. Hardware timing, rounding and ties can differ between machines.

The code is provided for inspection and reproducibility. No software license has yet been selected.
