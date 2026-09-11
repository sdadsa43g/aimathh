#!/usr/bin/env bash
# Run every demo; fail if any exit-coded demo fails.
set -u
mkdir -p data
pass=0; fail=0
for d in demos/demo*.py; do
  echo "=== $d ==="
  if python "$d" > "data/$(basename "$d" .py).log" 2>&1; then
    echo "PASS $d"; pass=$((pass+1))
  else
    echo "FAIL $d (see data/$(basename "$d" .py).log)"; fail=$((fail+1))
  fi
done
echo "demos: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
