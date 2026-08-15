#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, struct, time, zlib
from pathlib import Path
import numpy as np
from numba import njit

MAGIC=b'GCA2'; VERSION=2


def load_regular_ieee_segy(path: str):
    p=Path(path); size=p.stat().st_size
    with p.open('rb') as f:
        hdr=f.read(3600)
        if len(hdr)!=3600: raise ValueError('short SEG-Y header')
        ns=int.from_bytes(hdr[3220:3222],'big')
        fmt=int.from_bytes(hdr[3224:3226],'big')
        if ns<=0 or fmt!=5: raise ValueError(f'require regular IEEE float32 SEG-Y, ns={ns}, fmt={fmt}')
        stride=240+4*ns
        rem=size-3600
        if rem<=0 or rem%stride: raise ValueError('file is not fixed-length regular traces')
        ntr=rem//stride
        rows=[]; traces=[]
        for k in range(ntr):
            th=f.read(240)
            if len(th)!=240: raise EOFError(k)
            il=int.from_bytes(th[188:192],'big',signed=True)
            xl=int.from_bytes(th[192:196],'big',signed=True)
            b=f.read(4*ns)
            if len(b)!=4*ns: raise EOFError(k)
            rows.append((il,xl)); traces.append(np.frombuffer(b,dtype='>f4').astype(np.float32))
    ils=sorted(set(x[0] for x in rows)); xls=sorted(set(x[1] for x in rows))
    if len(ils)*len(xls)!=ntr: raise ValueError(('not a complete regular inline/xline grid',len(ils),len(xls),ntr))
    im={v:i for i,v in enumerate(ils)}; xm={v:i for i,v in enumerate(xls)}
    X=np.empty((len(ils),len(xls),ns),np.float32); seen=set()
    for key,a in zip(rows,traces):
        if key in seen: raise ValueError(('duplicate inline/xline',key))
        seen.add(key); X[im[key[0]],xm[key[1]]]=a
    return X, {'format':'SEG-Y','format_code':fmt,'inlines':len(ils),'xlines':len(xls),'samples_per_trace':ns,
               'trace_count':ntr,'inline_min':ils[0],'inline_max':ils[-1],'xline_min':xls[0],'xline_max':xls[-1],
               'source_bytes':size}


def predictor_specs():
    specs=[('zero',0)]
    specs += [('x',d) for d in range(-4,5)]
    specs += [('i',d) for d in range(-4,5)]
    specs += [('x2',d) for d in range(-2,3)]
    specs += [('i2',d) for d in range(-2,3)]
    specs += [('ix',d) for d in range(-2,3)]
    return specs


def legal_state_predict(X, eps):
    NI,NX,NT=X.shape; idx=np.arange(NT); specs=predictor_specs()
    Q=np.empty((NI,NX,NT),np.int32); R=np.empty_like(Q); M=np.empty((NI,NX),np.uint8)
    def sh(a,d): return a[np.clip(idx+d,0,NT-1)]
    def pred(i,j,spec):
        kind,d=spec
        if kind=='zero': return np.zeros(NT,np.int32)
        if kind=='x': return None if j<1 else sh(Q[i,j-1],d)
        if kind=='i': return None if i<1 else sh(Q[i-1,j],d)
        if kind=='x2': return None if j<2 else 2*sh(Q[i,j-1],d)-sh(Q[i,j-2],d)
        if kind=='i2': return None if i<2 else 2*sh(Q[i-1,j],d)-sh(Q[i-2,j],d)
        if kind=='ix': return None if (i<1 or j<1) else sh(Q[i,j-1],d)+sh(Q[i-1,j],d)-sh(Q[i-1,j-1],d)
        raise ValueError(kind)
    for i in range(NI):
        for j in range(NX):
            x=X[i,j].astype(np.float64)
            lo=np.ceil((x-eps)/eps-1e-12).astype(np.int32)
            hi=np.floor((x+eps)/eps+1e-12).astype(np.int32)
            best_score=None; best=None
            for m,spec in enumerate(specs):
                p=pred(i,j,spec)
                if p is None: continue
                q=np.minimum(np.maximum(p,lo),hi).astype(np.int32)
                r=q-p; a=np.abs(r.astype(np.int64))
                score=(int(np.count_nonzero(r)),int(a.sum()),int(np.dot(a,a)))
                if best_score is None or score<best_score:
                    best_score=score; best=(m,q,r)
            m,q,r=best; M[i,j]=m; Q[i,j]=q; R[i,j]=r
    return Q,R,M

@njit
def _emit(out,pos,bit):
    if bit: out[pos>>3] |= np.uint8(1 << (7-(pos&7)))
    return pos+1
@njit
def _read(inp,pos,nbits):
    if pos>=nbits:return 0,pos+1
    return int((inp[pos>>3]>>(7-(pos&7)))&1),pos+1

@njit
def _arith_encode(a,counts,B,C,maxbytes):
    out=np.zeros(maxbytes,np.uint8);pos=0;low=np.uint64(0);high=np.uint64(0xFFFFFFFF)
    HALF=np.uint64(0x80000000);Q1=np.uint64(0x40000000);Q3=np.uint64(0xC0000000);pending=0
    N=a.size;K=2*C+3
    for bi,s0 in enumerate(range(0,N,B)):
        n=min(B,N-s0); freq=np.empty(32,np.int64)
        for k in range(K):freq[k]=int(counts[bi,k])
        total=n
        for ii in range(n):
            v=int(a[s0+ii]); sym=v+C if -C<=v<=C else (2*C+1 if v<0 else 2*C+2)
            cum=0
            for k in range(sym):cum+=freq[k]
            f=freq[sym];rng=high-low+np.uint64(1)
            high=low+(rng*np.uint64(cum+f))//np.uint64(total)-np.uint64(1)
            low=low+(rng*np.uint64(cum))//np.uint64(total)
            while True:
                if high<HALF:
                    pos=_emit(out,pos,0)
                    for _ in range(pending):pos=_emit(out,pos,1)
                    pending=0
                elif low>=HALF:
                    pos=_emit(out,pos,1)
                    for _ in range(pending):pos=_emit(out,pos,0)
                    pending=0;low-=HALF;high-=HALF
                elif low>=Q1 and high<Q3:
                    pending+=1;low-=Q1;high-=Q1
                else: break
                low<<=np.uint64(1);high=(high<<np.uint64(1))+np.uint64(1)
            freq[sym]-=1;total-=1
    pending+=1
    if low<Q1:
        pos=_emit(out,pos,0)
        for _ in range(pending):pos=_emit(out,pos,1)
    else:
        pos=_emit(out,pos,1)
        for _ in range(pending):pos=_emit(out,pos,0)
    return out,pos

@njit
def _arith_decode(inp,nbits,counts,N,B,C):
    out=np.empty(N,np.int16);pos=0;low=np.uint64(0);high=np.uint64(0xFFFFFFFF);code=np.uint64(0)
    HALF=np.uint64(0x80000000);Q1=np.uint64(0x40000000);Q3=np.uint64(0xC0000000)
    for _ in range(32):
        b,pos=_read(inp,pos,nbits);code=(code<<np.uint64(1))|np.uint64(b)
    K=2*C+3
    for bi,s0 in enumerate(range(0,N,B)):
        n=min(B,N-s0);freq=np.empty(32,np.int64)
        for k in range(K):freq[k]=int(counts[bi,k])
        total=n
        for ii in range(n):
            rng=high-low+np.uint64(1);val=((code-low+np.uint64(1))*np.uint64(total)-np.uint64(1))//rng
            cum=0;sym=0
            for k in range(K):
                nxt=cum+freq[k]
                if val<np.uint64(nxt):sym=k;break
                cum=nxt
            f=freq[sym];high=low+(rng*np.uint64(cum+f))//np.uint64(total)-np.uint64(1);low=low+(rng*np.uint64(cum))//np.uint64(total)
            while True:
                if high<HALF:pass
                elif low>=HALF:low-=HALF;high-=HALF;code-=HALF
                elif low>=Q1 and high<Q3:low-=Q1;high-=Q1;code-=Q1
                else:break
                low<<=np.uint64(1);high=(high<<np.uint64(1))+np.uint64(1);b,pos=_read(inp,pos,nbits);code=(code<<np.uint64(1))|np.uint64(b)
            out[s0+ii]=sym;freq[sym]-=1;total-=1
    return out

@njit
def _gamma_len(n):
    L=0
    while n>0:L+=1;n>>=1
    return 2*L-1
@njit
def _tail_bits(a,C):
    z=0
    for v0 in a:
        v=int(v0);av=v if v>=0 else -v
        if av>C:z+=_gamma_len(av-C)
    return z
@njit
def _write_bits(out,pos,v,w):
    for j in range(w-1,-1,-1):pos=_emit(out,pos,(v>>j)&1)
    return pos
@njit
def _tail_encode(a,C,total):
    out=np.zeros((total+7)//8,np.uint8);pos=0
    for v0 in a:
        v=int(v0);av=v if v>=0 else -v
        if av>C:
            g=av-C;L=0;x=g
            while x>0:L+=1;x>>=1
            for _ in range(L-1):pos=_emit(out,pos,0)
            pos=_write_bits(out,pos,g,L)
    return out,pos
@njit
def _tail_decode(inp,nbits,nvals):
    vals=np.empty(nvals,np.int32);pos=0
    for i in range(nvals):
        zeros=0
        while True:
            b,pos=_read(inp,pos,nbits)
            if b:break
            zeros+=1
        L=zeros+1;g=1
        for _ in range(L-1):b,pos=_read(inp,pos,nbits);g=(g<<1)|b
        vals[i]=g
    return vals


def encode_array(X, eps, B=32768, C=3):
    Q,R,M=legal_state_predict(X,eps); flat=R.ravel();N=flat.size;K=2*C+3;nb=(N+B-1)//B
    counts=np.zeros((nb,K),np.uint16)
    for bi,s in enumerate(range(0,N,B)):
        a=flat[s:s+B];cat=np.empty(a.size,np.int16);sm=np.abs(a)<=C
        cat[sm]=a[sm]+C;cat[(~sm)&(a<0)]=2*C+1;cat[(~sm)&(a>0)]=2*C+2
        counts[bi]=np.bincount(cat,minlength=K)
    counts_z=zlib.compress(counts.tobytes(),6);mode_z=zlib.compress(M.tobytes(),6)
    catbuf,catbits=_arith_encode(flat,counts,B,C,max(1024,int(N*2)));catbuf=catbuf[:(catbits+7)//8]
    tb=int(_tail_bits(flat,C));tailbuf,tused=_tail_encode(flat,C,tb);assert int(tused)==tb
    NI,NX,NT=X.shape
    h0=struct.pack('<4sBHHHdIBIIQQ',MAGIC,VERSION,NI,NX,NT,float(eps),B,C,len(counts_z),len(mode_z),int(catbits),tb)
    blob=h0+bytes(64-len(h0))+counts_z+mode_z+catbuf.tobytes()+tailbuf.tobytes()
    return blob,{'q':Q,'residual':R,'modes':M,'zero_fraction':float(np.mean(R==0)),
                 'abs_le_2_fraction':float(np.mean(np.abs(R.astype(np.int64))<=2))}


def decode_array(blob: bytes):
    h=struct.unpack('<4sBHHHdIBIIQQ',blob[:struct.calcsize('<4sBHHHdIBIIQQ')])
    magic,ver,NI,NX,NT,eps,B,C,ncz,nmz,catbits,tb=h
    if magic!=MAGIC or ver!=VERSION:raise ValueError('bad GCA2 stream')
    N=NI*NX*NT;K=2*C+3;nb=(N+B-1)//B;off=64
    counts=np.frombuffer(zlib.decompress(blob[off:off+ncz]),np.uint16).reshape(nb,K);off+=ncz
    M=np.frombuffer(zlib.decompress(blob[off:off+nmz]),np.uint8).reshape(NI,NX);off+=nmz
    cb=(catbits+7)//8;catbuf=np.frombuffer(blob[off:off+cb],np.uint8);off+=cb
    tailbuf=np.frombuffer(blob[off:],np.uint8)
    cats=_arith_decode(catbuf,int(catbits),counts,N,B,C)
    ntail=int(np.count_nonzero(cats>2*C));mags=_tail_decode(tailbuf,int(tb),ntail)
    D=np.empty(N,np.int32);ti=0
    for k,s0 in enumerate(cats):
        s=int(s0)
        if s<=2*C:D[k]=s-C
        elif s==2*C+1:D[k]=-(C+int(mags[ti]));ti+=1
        else:D[k]=C+int(mags[ti]);ti+=1
    idx=np.arange(NT);specs=predictor_specs();Q=np.empty((NI,NX,NT),np.int32);DR=D.reshape(NI,NX,NT)
    def sh(a,d):return a[np.clip(idx+d,0,NT-1)]
    def pred(i,j,spec):
        kind,d=spec
        if kind=='zero':return np.zeros(NT,np.int32)
        if kind=='x':return sh(Q[i,j-1],d)
        if kind=='i':return sh(Q[i-1,j],d)
        if kind=='x2':return 2*sh(Q[i,j-1],d)-sh(Q[i,j-2],d)
        if kind=='i2':return 2*sh(Q[i-1,j],d)-sh(Q[i-2,j],d)
        if kind=='ix':return sh(Q[i,j-1],d)+sh(Q[i-1,j],d)-sh(Q[i-1,j-1],d)
    for i in range(NI):
        for j in range(NX):Q[i,j]=pred(i,j,specs[int(M[i,j])])+DR[i,j]
    return Q.astype(np.float64)*eps,{'shape':[NI,NX,NT],'epsilon':eps,'modes':M,'residual':DR,'q':Q}


def matched_sz3(X,eps):
    from pysz import sz,szConfig,szErrorBoundMode
    cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
    bb,_=sz.compress(np.ascontiguousarray(X),cfg);R,_=sz.decompress(bb,X.dtype,X.shape)
    me=float(np.max(np.abs(X.astype(np.float64)-R.astype(np.float64))))
    return int(bb.size),me


def run(path,out_stream=None,with_sz3=False):
    X,src=load_regular_ieee_segy(path);std=float(X.astype(np.float64).std());eps=.1*std
    t=time.time();blob,em=encode_array(X,eps);enc_s=time.time()-t
    t=time.time();Y,dm=decode_array(blob);dec_s=time.time()-t
    me=float(np.max(np.abs(X.astype(np.float64)-Y)))
    if me>eps*(1+3e-7):raise RuntimeError(('GCA2 hard bound',me,eps))
    if not np.array_equal(em['q'],dm['q']):raise RuntimeError('GCA2 decoder q mismatch')
    result={'engine':'gca_constraint_address_v2','source':src,'shape':list(X.shape),'samples':int(X.size),'numeric_bytes':int(X.nbytes),
            'std':std,'epsilon':eps,'gca2_bytes':len(blob),'gca2_bps':8*len(blob)/X.size,'gca2_numeric_ratio':X.nbytes/len(blob),
            'gca2_maxerr':me,'decoder_valid':True,'encode_seconds':enc_s,'decode_seconds':dec_s,
            'zero_fraction':em['zero_fraction'],'abs_le_2_fraction':em['abs_le_2_fraction'],'dataset_label_used_for_routing':False}
    if with_sz3:
        sb,sme=matched_sz3(X,eps);result.update({'sz3_bytes':sb,'sz3_maxerr':sme,'gain_sz3_over_gca2':sb/len(blob),
                                                'reduction_percent_vs_sz3':100*(1-len(blob)/sb)})
        if sme>eps*(1+3e-6):raise RuntimeError(('SZ3 hard bound',sme,eps))
    if out_stream:Path(out_stream).write_bytes(blob)
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('segy');ap.add_argument('--stream');ap.add_argument('--sz3',action='store_true');ap.add_argument('--json')
    a=ap.parse_args();r=run(a.segy,a.stream,a.sz3);txt=json.dumps(r,indent=2);print(txt)
    if a.json:Path(a.json).write_text(txt)
