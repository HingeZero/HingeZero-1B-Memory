#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
if [[ $# -ne 1 ]]; then echo 'Usage: bash run_1b.sh /absolute/path/to/new-bank.bin' >&2; exit 2; fi
BANK="$1"
[[ ! -e "$BANK" ]] || { echo 'Refusing to overwrite existing bank file'; exit 2; }
[[ -d "$(dirname "$BANK")" ]] || { echo 'Bank directory not found'; exit 2; }
g++ -std=c++20 -O3 HingeZero_Native_1B.cpp -o hz_native
LOG=reproduced_1b_run.log
: > "$LOG"
echo 'Creating original 900 million records' | tee -a "$LOG"
./hz_native create "$BANK" 900000000 | tee -a "$LOG"
BEFORE=$(sha256sum "$BANK" | awk '{print $1}')
echo "before_prefix_sha256=$BEFORE" | tee -a "$LOG"
echo 'Appending final 100 million' | tee -a "$LOG"
./hz_native append "$BANK" 900000000 100000000 | tee -a "$LOG"
AFTER=$(head -c 14400000000 "$BANK" | sha256sum | awk '{print $1}')
echo "after_prefix_sha256=$AFTER" | tee -a "$LOG"
[[ "$BEFORE" == "$AFTER" ]] || { echo 'FAIL: append changed original prefix'; exit 1; }
echo 'APPEND INTEGRITY PASS' | tee -a "$LOG"
for id in 417 777777777; do
 for regime in exact flip20 flip35 missing50 severe multi4; do
   echo "target=$id regime=$regime" | tee -a "$LOG"
   ./hz_native test "$BANK" 1000000000 "$id" "$regime" | tee -a "$LOG"
 done
done
echo FINISHED | tee -a "$LOG"
