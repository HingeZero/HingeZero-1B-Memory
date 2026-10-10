"""Verify the internally consistent recorded result counts from the CSV.
This is NOT a substitute for rerunning the billion-pattern benchmark.
"""
import csv
import pathlib
import statistics
p = pathlib.Path(__file__).resolve().parent / 'billion_results.csv'
rows = list(csv.DictReader(p.open(newline='')))
assert len(rows) == 12, f'Expected 12 recorded cases, got {len(rows)}'
assert {int(r['target']) for r in rows} == {417, 777777777}
assert {r['regime'] for r in rows} == {'exact','flip20','flip35','missing50','severe','multi4'}
assert all(r['witness'].lower() == 'true' for r in rows)
assert sum(r['correct'].lower() == 'true' for r in rows) == 8
assert all((int(r['selected']) == int(r['target'])) ==
           (r['correct'].lower() == 'true') for r in rows)
print('RECORDED CSV VERIFIED: 12 cases; 8 correct; 12 witnessed')
print('Median scan duration (seconds):',
      round(statistics.median(float(r['scan_ms']) for r in rows)/1000, 3))
print('Median refinement (milliseconds):',
      round(statistics.median(float(r['refine_ms']) for r in rows), 3))
