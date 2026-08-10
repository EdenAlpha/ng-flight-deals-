#!/usr/bin/env bash
set -euo pipefail
rm -rf paq8px-src paqbench && mkdir paqbench
git clone -q --depth 1 https://github.com/hxim/paq8px.git paq8px-src
cd paq8px-src/build
bash build-linux-with-cmake.sh >/dev/null
BIN="$PWD/paq8px"
cd ../..
python3 -m pip download -q --no-deps pygments==2.19.1 -d paqbench
WHEEL=$(realpath $(echo paqbench/*.whl))
# Same CSV corpus used by AXIOM: header + first 250,000 rows.
curl -L --retry 3 -sS https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-counties.csv -o paqbench/us-counties-full.csv
head -n 250001 paqbench/us-counties-full.csv > paqbench/data.csv
rm paqbench/us-counties-full.csv
python3 - <<'PY'
import os,pathlib
print('wheel',next(pathlib.Path('paqbench').glob('*.whl')).stat().st_size)
print('csv',os.path.getsize('paqbench/data.csv'))
PY
# Explicitly NO L flag: PAQ context-mixing reference without its optional LSTM model.
# -B asks its native DEFLATE detector to work harder on the wheel.
"$BIN" -8B "$WHEEL" paqbench/wheel.paq8px216 > paqbench/wheel.log
"$BIN" -8 paqbench/data.csv paqbench/csv.paq8px216 > paqbench/csv.log
mkdir -p paqbench/out
"$BIN" -d paqbench/wheel.paq8px216 paqbench/out/wheel.whl >/dev/null
"$BIN" -d paqbench/csv.paq8px216 paqbench/out/data.csv >/dev/null
cmp "$WHEEL" paqbench/out/wheel.whl
cmp paqbench/data.csv paqbench/out/data.csv
python3 - <<'PY'
import json,os,pathlib
wheel=next(pathlib.Path('paqbench').glob('*.whl'))
out={
 'paq8px_version':'v216 current branch; level -8; NO LSTM flag',
 'wheel':{'original':wheel.stat().st_size,'paq8px_non_lstm':os.path.getsize('paqbench/wheel.paq8px216'),'axiom':822924,'exact':True},
 'csv':{'original':os.path.getsize('paqbench/data.csv'),'paq8px_non_lstm':os.path.getsize('paqbench/csv.paq8px216'),'axiom':132510,'exact':True}
}
for k in ('wheel','csv'):
 p=out[k];p['axiom_vs_paq8px_pct']=round((p['paq8px_non_lstm']-p['axiom'])*100/p['paq8px_non_lstm'],2)
open('paqbench/paq8px_results.json','w').write(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
PY
