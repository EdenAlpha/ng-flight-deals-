#!/usr/bin/env python3
import os, json, struct, hashlib, time
from collections import Counter
from datasets import load_dataset
import sentencepiece as spm

TARGET = 100_000_000
MODEL = os.environ.get('CLM_TOKENIZER', '/tmp/clm_general_16k.model')
OUTDIR = 'clm_tulu3_100m'
OUT = os.path.join(OUTDIR, 'tulu3_100m.u16')
os.makedirs(OUTDIR, exist_ok=True)
sp = spm.SentencePieceProcessor(model_file=MODEL)
USER, ASSIST, EOD = 2, 3, 1

# Deliberately exclude data whose purpose conflicts with this clean conversation/reasoning experiment.
EXCLUDE = ('hard-coded', 'hardcoded', 'wildjailbreak', 'wildguard')

def englishish(s):
    if not s or len(s) < 2: return False
    letters = sum(c.isalpha() for c in s)
    ascii_chars = sum(ord(c) < 128 for c in s)
    return letters >= 2 and ascii_chars / max(1, len(s)) >= 0.82

def valid_example(ex):
    src = str(ex.get('source','')).lower()
    if any(x in src for x in EXCLUDE): return False
    msgs = ex.get('messages') or []
    has_u = any(m.get('role') == 'user' and englishish(str(m.get('content',''))) for m in msgs)
    has_a = any(m.get('role') == 'assistant' and englishish(str(m.get('content',''))) for m in msgs)
    return has_u and has_a

def encode_example(ex):
    ids=[]
    for m in ex.get('messages') or []:
        role=m.get('role'); text=str(m.get('content','')).strip()
        if role not in ('user','assistant') or not text: continue
        if role == 'user': ids.append(USER)
        else: ids.append(ASSIST)
        ids.extend(sp.encode(text, out_type=int))
    if ASSIST not in ids or USER not in ids: return []
    ids.append(EOD)
    return ids

# Streaming + deterministic shuffle avoids downloading the full 1.4GB parquet collection to RAM.
ds = load_dataset('allenai/tulu-3-sft-mixture', split='train', streaming=True)
ds = ds.shuffle(seed=20260815, buffer_size=20_000)
source_tokens=Counter(); source_examples=Counter(); total=0; accepted=0; seen=0
sha=hashlib.sha256(); t0=time.time()
with open(OUT,'wb',buffering=4*1024*1024) as f:
    for ex in ds:
        seen += 1
        if not valid_example(ex): continue
        ids=encode_example(ex)
        if not ids: continue
        remain=TARGET-total
        if len(ids)>remain:
            # Never cut a conversation into a fake assistant turn. Fill the final remainder only
            # if the whole example fits; otherwise keep scanning for a shorter example.
            if remain < 8: break
            continue
        b=struct.pack('<%dH'%len(ids),*ids)
        f.write(b); sha.update(b)
        total += len(ids); accepted += 1
        src=str(ex.get('source','unknown')); source_tokens[src]+=len(ids); source_examples[src]+=1
        if accepted % 5000 == 0:
            print(json.dumps({'tokens':total,'accepted':accepted,'seen':seen,'seconds':round(time.time()-t0,1)}), flush=True)
        if total >= TARGET: break

# If exact target was not naturally hit, pad ONLY with EOD document separators. These do not
# create language targets and make the binary length deterministic/exact.
if total < TARGET:
    pad=TARGET-total
    with open(OUT,'ab') as f:
        b=struct.pack('<%dH'%pad,*([EOD]*pad)); f.write(b); sha.update(b)
    total=TARGET

manifest={
 'name':'CLM Tulu3 paired instruction corpus',
 'tokens':total,
 'bytes':os.path.getsize(OUT),
 'tokenizer':'clm_general_16k.model',
 'vocab_size':sp.vocab_size(),
 'sha256':sha.hexdigest(),
 'accepted_examples':accepted,
 'seen_examples':seen,
 'excluded_source_substrings':list(EXCLUDE),
 'source_tokens':dict(source_tokens),
 'source_examples':dict(source_examples),
 'hardcoded_answers_added_by_builder':False,
}
with open(os.path.join(OUTDIR,'manifest.json'),'w') as f: json.dump(manifest,f,indent=2,sort_keys=True)
with open(os.path.join(OUTDIR,'README.txt'),'w') as f:
    f.write('100M-token English-heavy paired instruction corpus from allenai/tulu-3-sft-mixture.\n')
    f.write('Uses the existing CLM general 16k tokenizer. Hardcoded/WildJailbreak/WildGuard sources excluded.\n')
print(json.dumps(manifest,indent=2),flush=True)
