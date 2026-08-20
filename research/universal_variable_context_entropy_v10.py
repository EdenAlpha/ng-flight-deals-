#!/usr/bin/env python3
from __future__ import annotations
import json,struct,sys
from collections import defaultdict
import h5py,numpy as np
import universal_rate_searched_predictor_v1 as u
import imperial_defect_restricted_rank_address as rr
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m
import imperial_fair_ar_coarse_prefix_container as fair

A=u.A
TAG=241
V7_BYTES=22382
DEPTHS=(4,8,12,16)
MINS=(2,4,8)
SCANS=('tc','ct')
PREFIX=('none','bucket','exact')


def order_indices(shape,scan):
    nc,nt=shape
    if scan=='tc':return [(c,t) for t in range(nt) for c in range(nc)]
    return [(c,t) for c in range(nc) for t in range(nt)]


def pcat(known,bit,c,t,mode):
    if mode=='none':return 0
    p=int(known[c,t]>>(bit+1))
    if mode=='bucket':return min(15,p)
    return p


def key_for(hist,depth,prefix):
    d=min(depth,len(hist));x=0
    for b in hist[-d:]:x=(x<<1)|int(b)
    return (prefix,d,x)


def ppm_encode(B,known,bit,depth,mincount,scan,pmode):
    ae=rr.ArithEncoder();counts=defaultdict(lambda:[1,1]);hist=[];order=order_indices(B.shape,scan)
    for c,t in order:
        pref=pcat(known,bit,c,t,pmode);chosen=None
        for d in range(min(depth,len(hist)),-1,-1):
            k=key_for(hist,d,pref);z,o=counts[k]
            if d==0 or z+o-2>=mincount:
                chosen=k;break
        z,o=counts[chosen];b=int(B[c,t]);ae.encode(b,z,o)
        counts[chosen][b]+=1;hist.append(b)
    raw,nbits=ae.finish();zz=m.Z.compress(raw)
    if len(zz)<len(raw):am=1;store=zz
    else:am=0;store=raw
    scanid=SCANS.index(scan);pmid=PREFIX.index(pmode)
    payload=bytearray([TAG,depth,mincount,scanid,pmid]);payload.extend(struct.pack('<BII',am,int(nbits),len(store)));payload.extend(store)
    return bytes(payload),{'source':'vctx','depth':depth,'mincount':mincount,'scan':scan,'prefix_mode':pmode,'groups':len(counts),'arith_bits':int(nbits),'stored':len(payload)}


def ppm_decode(buf,off,known,bit,shape):
    depth=int(buf[off]);mincount=int(buf[off+1]);scan=SCANS[int(buf[off+2])];pmode=PREFIX[int(buf[off+3])];off+=4
    am,nbits,n=struct.unpack_from('<BII',buf,off);off+=9;store=buf[off:off+n];off+=n;raw=m.D.decompress(store) if am else store
    ad=rr.ArithDecoder(raw,nbits);counts=defaultdict(lambda:[1,1]);hist=[];B=np.zeros(shape,np.uint8)
    for c,t in order_indices(shape,scan):
        pref=pcat(known,bit,c,t,pmode);chosen=None
        for d in range(min(depth,len(hist)),-1,-1):
            k=key_for(hist,d,pref);z,o=counts[k]
            if d==0 or z+o-2>=mincount:
                chosen=k;break
        z,o=counts[chosen];b=ad.decode(z,o);B[c,t]=b;counts[chosen][b]+=1;hist.append(int(b))
    return B,off


def frame(K):
    K=np.asarray(K,np.int32);z=m.zig(K);mx=int(z.max()) if z.size else 0;nb=max(1,mx.bit_length());known=np.zeros_like(z,np.uint64)
    out=bytearray(struct.pack('<4sHHB',b'HRA3',K.shape[0],K.shape[1],nb));detail=[]
    for bit in range(nb-1,-1,-1):
        B=((z>>bit)&1).astype(np.uint8);best=None
        for fid in range(len(rr.FAMILIES)):
            payload,d=rr.encode_candidate(B,known,bit,fid);row=(payload,{'source':'incumbent-rank',**d})
            if best is None or len(payload)<len(best[0]):best=row
        for afid in range(len(A.ADAPT)):
            payload,d=A.encode_adaptive(B,known,bit,afid);row=(payload,{'source':'incumbent-adaptive',**d})
            if len(payload)<len(best[0]):best=row
        for depth in DEPTHS:
            for mc in MINS:
                for scan in SCANS:
                    for pm in PREFIX:
                        payload,d=ppm_encode(B,known,bit,depth,mc,scan,pm);row=(payload,d)
                        if len(payload)<len(best[0]):best=row
        payload,d=best;out.extend(payload);detail.append({'bit':bit,'payload_bytes':len(payload),**d});known|=B.astype(np.uint64)<<bit
        print('PLANE',json.dumps(detail[-1]),flush=True)
    buf=bytes(out);off=0;magic,nc,nt,nb2=struct.unpack_from('<4sHHB',buf,off);off+=9
    if magic!=b'HRA3' or (nc,nt)!=K.shape or nb2!=nb:raise RuntimeError('header')
    zz=np.zeros_like(z,np.uint64)
    for bit in range(nb-1,-1,-1):
        tag=int(buf[off]);off+=1
        if tag<TAG:
            if tag<16:B,off=A.decode_rank_payload(buf,off,zz,bit,tag,K.shape)
            else:
                if tag>=16+len(A.ADAPT):raise RuntimeError(('tag',tag))
                B,off=A.decode_adaptive_payload(buf,off,zz,bit,tag,K.shape)
        else:
            if tag!=TAG:raise RuntimeError(('vctx tag',tag))
            B,off=ppm_decode(buf,off,zz,bit,K.shape)
        zz|=B.astype(np.uint64)<<bit
    if off!=len(buf):raise RuntimeError(('trailing',off,len(buf)))
    Kd=m.unzig(zz).astype(np.int32)
    if not np.array_equal(Kd,K):raise RuntimeError('K replay')
    return len(buf),Kd,detail


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std;X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);offs,co,sbest,shist=u.search_sample(X);_,R,K,mb,ob,cod=sbest
    old,_,_=u.exact_field(K);new,Kd,planes=frame(K)
    Rd=np.zeros(K.shape,np.int32)
    for t in range(K.shape[1]):
        for c in range(K.shape[0]):Rd[c,t]=u.sample_pred(Rd,c,t,cod,offs)+u.STEP*int(Kd[c,t])
    if not np.array_equal(Rd,R):raise RuntimeError('replay')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    total=fair.COMMON_HEADER+1+len(ob)+len(mb)+new
    out={'kind':'universal-variable-context-entropy-v10','shape':list(X.shape),'eps':eps,'step':u.STEP,'bytes':int(total),'field_bytes':int(new),'old_field_bytes':int(old),'v7_bytes':V7_BYTES,'sz3_bytes':int(szb),'sz3_orientation':ori,'gain_vs_sz3':float(szb/total),'gain_vs_v7':float(V7_BYTES/total),'maxerr':me,'planes':planes,'principle':'Per residual bitplane, retain all incumbent entropy models as a strict floor and also test a universal online variable-order Markov coder. It chooses the deepest sufficiently observed suffix context, optionally conditioned on decoder-known higher-bit prefix, with no trained model or probability table transmitted.'}
    json.dump(out,open('universal_variable_context_entropy_v10.json','w'),indent=2);print('FINAL',json.dumps({k:v for k,v in out.items() if k!='planes'},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
