#!/usr/bin/env python3
import os,subprocess,base64,glob,zipfile,tempfile,lzma,shutil,time,json,sys
try: import brotli
except Exception: brotli=None
ROOT=os.path.dirname(os.path.abspath(__file__)); REPO=os.path.dirname(ROOT); OUT=os.path.join(ROOT,'out'); os.makedirs(OUT,exist_ok=True)
def sh(cmd): return subprocess.run(['bash','-lc',cmd],check=True,capture_output=True)
# Recover the validated v0.3 source carried by the research branch.
corrupt='/tmp/v03_corrupt.zip'
with open(corrupt,'wb') as o:
    for fn in sorted(glob.glob(os.path.join(REPO,'v03_chunks','part*.b64'))): o.write(base64.b64decode(open(fn,'rb').read()))
SRC='/tmp/v03src';shutil.rmtree(SRC,ignore_errors=True);os.makedirs(SRC)
subprocess.run(['unzip','-o',corrupt,'-d',SRC],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
# Repair known damaged TAR helper; CSV source is validated.
if os.path.exists(os.path.join(REPO,'axiom_recovery','tar_transform.py')): shutil.copy(os.path.join(REPO,'axiom_recovery','tar_transform.py'),SRC)
# Create v5 keyed-coordinate CSV graph: same law, but residuals are serialized by entity key,
# a free permutation because the already-decoded key columns deterministically define membership.
p=os.path.join(SRC,'csv_graph_transform.py'); s=open(p).read()
insert=r'''
def _pack_group_int_clustered(vals,cols,keyids):
    groups={};order=[]
    for i,v in enumerate(vals):
        key=tuple(cols[k][i] for k in keyids)
        if key not in groups:groups[key]=[];order.append(key)
        groups[key].append((i,v))
    bits=bytearray((len(vals)+7)//8);stream=bytearray();qpos=0
    for key in order:
        prev=0
        for _,v in groups[key]:
            if v==b'':qpos+=1;continue
            if not INT.fullmatch(v):return None
            q=int(v)
            if str(q).encode()!=v:return None
            bits[qpos>>3]|=1<<(qpos&7);qpos+=1
            stream+=enc_svar(q-prev);prev=q
    return b'H'+vi(len(keyids))+b''.join(vi(k) for k in keyids)+vi(len(bits))+bits+stream

def _unpack_group_int_clustered(rep,n,cols):
    p=1;nk,p=uv(rep,p);kids=[]
    for _ in range(nk):k,p=uv(rep,p);kids.append(k)
    bl,p=uv(rep,p);bits=rep[p:p+bl];p+=bl
    groups={};order=[]
    for i in range(n):
        key=tuple(cols[k][i] for k in kids)
        if key not in groups:groups[key]=[];order.append(key)
        groups[key].append(i)
    out=[None]*n;qpos=0
    for key in order:
        prev=0
        for i in groups[key]:
            if not ((bits[qpos>>3]>>(qpos&7))&1):out[i]=b'';qpos+=1;continue
            qpos+=1;d,p=dec_svar(rep,p);q=prev+d;prev=q;out[i]=str(q).encode()
    if p!=len(rep) or any(x is None for x in out):raise ValueError('cluster group trailing')
    return out
'''
s=s.replace('def _pack_fd(vals,cols,keyids):',insert+'\ndef _pack_fd(vals,cols,keyids):')
s=s.replace("            q=_pack_group_int(c,cols,ks)\n            if q:cand.append(q)","            q=_pack_group_int(c,cols,ks)\n            if q:cand.append(q)\n            q=_pack_group_int_clustered(c,cols,ks)\n            if q:cand.append(q)")
s=s.replace("        elif t==b'G':vals=_unpack_group_int(r,nr,cols)","        elif t==b'G':vals=_unpack_group_int(r,nr,cols)\n        elif t==b'H':vals=_unpack_group_int_clustered(r,nr,cols)")
open(os.path.join(SRC,'csv_graph_transform_v5.py'),'w').write(s)
sys.path.insert(0,SRC);import csv_graph_transform_v5 as csv5
# Rebuild the exact fixed corpus.
rawcsv='/tmp/all.csv';data='/tmp/data.csv'
subprocess.run(['curl','-L','--retry','3','-sS','https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-counties.csv','-o',rawcsv],check=True)
subprocess.run(['bash','-lc',f'head -n 250001 {rawcsv} > {data}'],check=True)
D=open(data,'rb').read();t=time.time();R=csv5.pack(D);pack_s=time.time()-t
exact=csv5.unpack(R)==D
if not exact:raise SystemExit('roundtrip failed')
open('/tmp/csv5.rep','wb').write(R)
def sizes(blob,tag):
    td=tempfile.mkdtemp();f=os.path.join(td,'x');open(f,'wb').write(blob);o={}
    subprocess.run(['xz','-9e','-k','-f',f],check=True);o['xz9e']=os.path.getsize(f+'.xz')
    subprocess.run(['brotli','-q','11','-f',f,'-o',f+'.br'],check=True);o['brotli11']=os.path.getsize(f+'.br')
    subprocess.run(['zstd','-22','--ultra','-q','-f',f,'-o',f+'.zst'],check=True);o['zstd22']=os.path.getsize(f+'.zst')
    shutil.rmtree(td);return o
raws=sizes(D,'raw');reps=sizes(R,'rep');rb=min(raws.values());ab=min(reps.values())
res={'category':'csv_graph_v5','original':len(D),'representation':len(R),'raw':raws,'axiom':reps,'raw_best':rb,'axiom_best':ab,'win_pct':round((rb-ab)*100/rb,2),'exact':exact,'pack_s':round(pack_s,2)}
print('RESULT',json.dumps(res),flush=True);open(os.path.join(OUT,'csv_v5.json'),'w').write(json.dumps(res,indent=2))
