#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
g++ -std=c++20 -O3 HingeZero_Native_1B.cpp -o hz_native
WORK=$(mktemp -d "${TMPDIR:-/tmp}/hz_smoke.XXXXXX")
trap 'rm -rf "$WORK"' EXIT
BANK="$WORK/memory_bank.bin"
./hz_native create "$BANK" 8192
BEFORE=$(sha256sum "$BANK" | awk '{print $1}')
./hz_native append "$BANK" 8192 256
AFTER=$(head -c 131072 "$BANK" | sha256sum | awk '{print $1}')
[[ "$BEFORE" == "$AFTER" ]] || { echo 'FAIL: existing records changed'; exit 1; }
./hz_native check "$BANK" 8448 417 > "$WORK/check.json"
./hz_native test "$BANK" 8448 417 exact > "$WORK/exact.json"
./hz_native test "$BANK" 8448 417 flip20 > "$WORK/flip20.json"
python3 - "$WORK" <<'PY'
import json, pathlib, sys
d = pathlib.Path(sys.argv[1])
check = json.loads((d/'check.json').read_text())
exact = json.loads((d/'exact.json').read_text())
flip = json.loads((d/'flip20.json').read_text())
assert check['accepted'] is True
assert exact['correct'] is True and exact['witness'] is True
assert flip['correct'] is True and flip['witness'] is True
print('SMOKE TEST PASS: append preservation, witness verification, exact and flip20 retrieval')
PY
