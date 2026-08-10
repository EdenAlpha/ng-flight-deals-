#!/usr/bin/env bash
set -euo pipefail
python3 -m pip download -q --no-deps pygments==2.19.1 -d wheel
WHEEL=$(realpath $(echo wheel/*.whl))
ORIG=$(stat -c%s "$WHEEL")
git clone -q --depth 1 https://github.com/microsoft/preflate-rs.git preflate
cd preflate
python3 - <<'PY'
p='util/src/main.rs'
s=open(p).read()
needle='        let stats = ctx.stats();\n'
repl='        println!("PREFLATE_CONTAINER_BYTES {}", preflate_compressed.len());\n\n        let stats = ctx.stats();\n'
assert needle in s
open(p,'w').write(s.replace(needle,repl,1))
PY
cargo build --release -q -p preflate_util
BIN="$PWD/target/release/preflate_util"
cd ..
$BIN "$WHEEL" -c 14 --baseline | tee preflate.log
SIZE=$(grep 'PREFLATE_CONTAINER_BYTES' preflate.log | tail -1 | awk '{print $2}')
python3 - <<PY
import json
orig=$ORIG
size=int('$SIZE')
axiom=822924
out={'corpus':'pygments-2.19.1 wheel','original':orig,'preflate_level14':size,'axiom_previous':axiom,'axiom_vs_preflate_pct':round((size-axiom)*100/size,2)}
open('preflate_results.json','w').write(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
PY
