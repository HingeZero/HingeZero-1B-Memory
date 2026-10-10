# Sealed native C++20 billion-memory run

**Frozen before executing final bank:**
- Implementation: `HingeZero_Native_1B.cpp`, compiled C++20, with dual tanh (α=4.5), ε=.10, λ=.02, 8 steps, fixed first 256 bank rows as field, global full-bank cosine dot-product selector, exact tagged-state witness.
- Binary bipolar patterns, 128 dimensions, deterministic splitmix64 pseudo-random bank (not a clinical or semantic workload).
- Create 900,000,000 records then append 100,000,000 records in physical file; compare the SHA-256 hash of the original 14.4-billion-byte prefix (900M records) before and after append.
- Two target rows, **417** (early memory) and **777,777,777** (old pre-append memory), fixed before final run.
- Six cue regimes per target: exact, 20% bit flips, 35% bit flips, 50% missing, single severely damaged (75% missing, 6 flips), four independent severely damaged cues.
- All 12 queries score every row in the full 1B bank with the same HingeZero configuration. Accuracy, global scan wall time, refinement wall time and tagged witness outputs reported independently.
- No external shortlist and no Hamming preselection. The full-bank native decoder uses streamed cosine (dot product on normalized bipolar vectors) with an arithmetic byte lookup accelerator.
- Additional fixed, unmodified Python-core parity test: compare C++ refined vectors and final identifiers on five smaller-bank cues; success requires 5/5 identical identifiers and coordinate max abs difference < 5e-5. Already completed before billion run.
- Success claims: actual 1B storage and native final scoring if all stages execute; retention if prefix hashes equal; witness if all 12 outputs verify; performance and recall as measured. No automatic claims of independent domain generalisation, sub-second response or improved accuracy attributable to dual tanh.
