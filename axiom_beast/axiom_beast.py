#!/usr/bin/env python3
import argparse,hashlib,os,sys,tempfile,shutil,subprocess,lzma,zlib
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import axiom3_common as C
import csv_graph_transform_v8 as CSV
import json_graph_transform_v6 as JSON
import tar_graph_transform as TAR
import text_transform as TEXT
import axiom2 as AX2
import image_ancestry_transform as IMG
import video_context_transform as VIDEO
import elf_graph_transform as ELF
MAGIC=b'AXB9'
EFFORT='max'
MODES={0:'raw',1:'csv-law-coordinate',2:'json-causal-graph',3:'tar-nested-law-graph',4:'text-band',5:'zip-generative-law',6:'rgb-codec-ancestry',7:'yuv-causal-context',8:'elf-instruction-coordinate-graph'}

def vi(n):return C.vi(n)
def uv(b,p=0):return C.uv(b,p)

def backend_candidates(d):
    out=[]
    if EFFORT=='fast':
        if shutil.which('zstd'):
            try:return [(1,C.zc(d,level=9))]
            except Exception:pass
        return [(2,lzma.compress(d,preset=6))]
    # Maximum-ratio mode: let strong backends compete.
    try: out.append((2,lzma.compress(d,preset=9|lzma.PRESET_EXTREME)))
    except Exception: pass
    if shutil.which('zstd'):
        try: out.append((1,C.zc(d)))
        except Exception: pass
    if shutil.which('brotli') or getattr(C,'_pybrotli',None) is not None:
        try: out.append((3,C.bc(d)))
        except Exception: pass
    if not out: raise RuntimeError('no compression backend')
    return out

def enc_stream(d):
    cid,c=min(backend_candidates(d),key=lambda x:len(x[1]))
    return cid,c

def dec_stream(cid,d):return C.dec(cid,d)

def pack_axm2(d):
    td=tempfile.mkdtemp();src=os.path.join(td,'in');dst=os.path.join(td,'x.axm')
    try:
        open(src,'wb').write(d);info=AX2.compress(src,dst);q=open(dst,'rb').read();return q,info
    finally:shutil.rmtree(td,ignore_errors=True)

def unpack_axm2(q):
    td=tempfile.mkdtemp();src=os.path.join(td,'x.axm');dst=os.path.join(td,'out')
    try:
        open(src,'wb').write(q);AX2.decompress(src,dst);return open(dst,'rb').read()
    finally:shutil.rmtree(td,ignore_errors=True)

def _looks_text(d):
    if not d:return False
    s=d[:65536]
    if b'\0' in s:return False
    return sum((x in b'\t\n\r' or 32<=x<127) for x in s)/len(s)>.90

def transform_candidates(d,name=''):
    ext=os.path.splitext(name.lower())[1]
    out=[]
    # Typed transforms are fail-closed and mutually exclusive. Once a structural grammar
    # recognizes an object we do not waste search budget pretending it is another format.
    is_zip = d[:4]==b'PK\x03\x04' or ext in {'.zip','.jar','.whl','.apk','.docx','.xlsx','.pptx','.epub'}
    is_tar = ext=='.tar' or (len(d)>=512 and d[257:262] in (b'ustar',b'ustar\x00'))
    is_json = ext=='.json' or d.lstrip()[:1] in (b'[',b'{')
    is_csv = ext=='.csv' or (not is_json and not is_tar and not is_zip and b',' in d[:4096] and b'\n' in d[:4096])
    is_elf = d[:4]==b'\x7fELF'
    if is_elf:
        try:
            r=ELF.pack(d)
            if r is not None: out.append((8,r,{}))
        except Exception: pass
    elif is_csv:
        try:
            r=CSV.pack(d)
            if r is not None and CSV.unpack(r)==d: out.append((1,r,{}))
        except Exception: pass
    elif is_json:
        try:
            r=JSON.pack(d)
            if r is not None and JSON.unpack(r)==d: out.append((2,r,{}))
        except Exception: pass
    elif is_tar:
        try:
            r=TAR.pack(d)
            if r is not None and TAR.unpack(r)==d: out.append((3,r,{}))
        except Exception: pass
    elif (not is_zip) and (ext in {'.yuv','.yuv420','.yuv420p'} or (ext=='.raw' and len(d)>4*1024*1024)):
        try:
            r=VIDEO.pack(d)
            if r is not None: out.append((7,r,{}))
        except Exception: pass
    elif (not is_zip) and ext in {'.raw','.rgb','.rgb24'} and len(d) <= 4*1024*1024:
        try:
            r=IMG.pack(d)
            if r is not None and IMG.unpack(r)==d: out.append((6,r,{}))
        except Exception: pass
    elif (not is_zip) and (ext in {'.txt','.md','.log','.sql','.xml','.html','.css','.js','.py','.java','.kt','.c','.cpp','.h'} or _looks_text(d)):
        try:
            for r in TEXT.candidates(d):
                if TEXT.unpack(r)==d: out.append((4,r,{}))
        except Exception: pass
    elif is_zip:
        try:
            q,info=pack_axm2(d)
            if info.get('mode')=='zip-law' and unpack_axm2(q)==d: out.append((5,q,{'peeled':info.get('peeled',0)}))
        except Exception: pass
    return out

def compress(src,dst):
    d=open(src,'rb').read();name=os.path.basename(src);digest=hashlib.sha256(d).digest()
    transforms=transform_candidates(d,name)
    # Two-stage MDL selection. A reversible structural representation gets an inexpensive
    # DEFLATE proxy first. If it is overwhelmingly cheaper, the raw representation is
    # pruned before expensive XZ/Brotli search. This changes search cost, never semantics.
    raw_proxy=len(zlib.compress(d,6)) if d else 0
    strong=[]
    for mode,rep,meta in transforms:
        proxy=len(rep) if mode in (5,6,7) else len(zlib.compress(rep,6))
        strong.append((proxy,mode,rep,meta))
    prune_raw=bool(strong and min(x[0] for x in strong) < raw_proxy*0.82)
    if prune_raw:
        best=(10**30,0,0,b'',{},len(d))
    else:
        rcid,rawc=enc_stream(d);best=(len(rawc),0,rcid,rawc,{},len(d))
    # Spend strong entropy coding only on structural candidates whose cheap proxy is
    # plausibly competitive with the best proxy.
    if strong:
        bp=min(x[0] for x in strong)
        strong=[x for x in strong if x[0] <= bp*1.15]
    for proxy,mode,rep,meta in strong:
        if mode in (5,6,7): cid=0;c=rep
        else: cid,c=enc_stream(rep)
        cand=(len(c),mode,cid,c,meta,len(rep))
        if cand[0]<best[0]:best=cand
    _,mode,cid,c,meta,replen=best
    out=bytearray(MAGIC)+vi(len(d))+digest+bytes([mode,cid])+vi(len(c))+c
    open(dst,'wb').write(out)
    return {'original':len(d),'compressed':len(out),'ratio':round(len(d)/len(out),4) if out else 0,'mode':MODES[mode],'backend':cid,'representation':replen,**meta}

def decompress(src,dst):
    b=open(src,'rb').read()
    if b[:4] not in (b'AXB7',MAGIC):raise ValueError('bad AXIOM Beast magic')
    p=4;orig,p=uv(b,p);digest=b[p:p+32];p+=32;mode=b[p];cid=b[p+1];p+=2;cl,p=uv(b,p);c=b[p:p+cl];p+=cl
    if p!=len(b):raise ValueError('trailing archive data')
    if mode==5:d=unpack_axm2(c)
    elif mode==6:d=IMG.unpack(c)
    elif mode==7:d=VIDEO.unpack(c)
    else:
        rep=dec_stream(cid,c)
        if mode==0:d=rep
        elif mode==1:d=CSV.unpack(rep)
        elif mode==2:d=JSON.unpack(rep)
        elif mode==3:d=TAR.unpack(rep)
        elif mode==4:d=TEXT.unpack(rep)
        elif mode==8:d=ELF.unpack(rep)
        else:raise ValueError('unknown AXIOM mode')
    if len(d)!=orig or hashlib.sha256(d).digest()!=digest:raise ValueError('AXIOM integrity failure')
    open(dst,'wb').write(d);return {'output':len(d),'mode':MODES[mode]}

def main():
    ap=argparse.ArgumentParser(description='AXIOM Beast v0.12 non-AI generative-law lossless compressor')
    sp=ap.add_subparsers(dest='cmd',required=True)
    a=sp.add_parser('c');a.add_argument('src');a.add_argument('dst');a.add_argument('--effort',choices=['fast','max'],default='max')
    a=sp.add_parser('d');a.add_argument('src');a.add_argument('dst')
    q=ap.parse_args();
    global EFFORT
    if q.cmd=='c': EFFORT=q.effort
    print(compress(q.src,q.dst) if q.cmd=='c' else decompress(q.src,q.dst))
if __name__=='__main__':main()
