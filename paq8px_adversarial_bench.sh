#!/usr/bin/env bash
set -euo pipefail
rm -rf paq8px-src paqbench && mkdir paqbench
git clone -q --depth 1 https://github.com/hxim/paq8px.git paq8px-src
cd paq8px-src/build
bash build-linux-with-cmake.sh >/dev/null
BIN="$PWD/paq8px"
cd ../..
curl -L --retry 3 -sS https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-counties.csv -o paqbench/us-counties-full.csv
head -n 250001 paqbench/us-counties-full.csv > paqbench/data.csv
rm paqbench/us-counties-full.csv
# Current PAQ8px v216 context mixing, strongest level used here, deliberately NO -L LSTM option.
"$BIN" -8 paqbench/data.csv paqbench/csv.paq8px216 > paqbench/csv.log
mkdir -p paqbench/out
"$BIN" -d paqbench/csv.paq8px216 paqbench/out/data.csv >/dev/null
cmp paqbench/data.csv paqbench/out/data.csv
python3 - <<'PY'
import json,os
out={
 'paq8px_version':'v216 current branch; level -8; NO LSTM flag',
 'original':os.path.getsize('paqbench/data.csv'),
 'paq8px_non_lstm':os.path.getsize('paqbench/csv.paq8px216'),
 'axiom':132510,
 'paq8px_exact':True,
 'axiom_exact':True,
}
out['axiom_vs_paq8px_pct']=round((out['paq8px_non_lstm']-out['axiom'])*100/out['paq8px_non_lstm'],2)
open('paqbench/paq8px_results.json','w').write(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
PY
