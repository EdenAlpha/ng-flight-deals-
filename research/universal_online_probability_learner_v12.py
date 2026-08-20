#!/usr/bin/env python3
from __future__ import annotations
import json,math,struct,sys
import h5py,numpy as np
import universal_rate_searched_predictor_v1 as u
import universal_auto_entropy_context_v7 as v7
import imperial_defect_restricted_rank_address as rr
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m
import imperial_fair_ar_coarse_prefix_container as fair

A=u.A
NEURAL_TAG=241
TOT=4096
WCLIP=1024
QMAX=64
# Public feature vocabulary: all are decoder-known when the bit is coded.
FPRIMS=(0,1,10,11,12,14,15,20,21,22,30,31,34,35,36,37,40,41,42,43,44,45,50,51,60,61,62)
PAIR_POS=((0,2),(0,7),(0,16),(2,7),(2,16),(7,16),(16,17),(20,21),(23,24))
CONFIGS=(
    {'dim':256,'lr_shift':10,'score_shift':5,'pairs':0},
    {'dim':512,'lr_shift':10,'score_shift':5,'pairs':1},
    {'dim':1024,'lr_shift':10,'score_shift':5,'pairs':1},
    {'dim':1024,'lr_shift':11,'score_shift':4,'pairs':1},
    {'dim':2048,'lr_shift':11,'score_shift':5,'pairs':1},
)
SIG=[]
for q in range(-QMAX,QMAX+1):
    p=1.0/(1.0+math.exp(-float(q)/8.0));SIG.append(max(1,min(TOT-1,int(round(TOT*p)))))
COST1=np.array([-math.log2(p/TOT) for p in range(1,TOT)],np.float64)
COST0=np.array([-math.log2((TOT-p)/TOT) for p in range(1,TOT)],np.float64)

def hmix(a,b,d):
    x=(int(a)*0x9E3779B1) ^ ((int(b)+0x7F4A7C15)*0x85EBCA77)
    x ^= (x>>16);x=(x*0xC2B2AE3D)&0xffffffff;x^=(x>>13)
    return 1+(x%(d-1))

def pair_hash(a,va,b,vb,d):
    x=(int(a)*1315423911)^(int(b)*2654435761)^((int(va)+19)*2246822519)^((int(vb)+23)*3266489917)
    x&=0xffffffff;x^=(x>>15);x=(x*0x85EBCA6B)&0xffffffff
    return 1+(x%(d-1))

def feat_idx(known,B,bit,c,t,cfg):
    d=cfg['dim'];vals=[v7.pval(code,known,B,bit,c,t) for code in FPRIMS]
    z=[0]
    for code,val in zip(FPRIMS,vals):z.append(hmix(code,val,d))
    if cfg['pairs']:
        for i,j in PAIR_POS:
            z.append(pair_hash(FPRIMS[i],vals[i],FPRIMS[j],vals[j],d))
    # Preserve multiplicity only once; collisions should not silently amplify learning.
    return tuple(dict.fromkeys(z))

def model_prob(w,idx,cfg):
    s=0
    for j in idx:s+=int(w[j])
    q=s>>cfg['score_shift']
    if q<-QMAX:q=-QMAX
    elif q>QMAX:q=QMAX
    p1=SIG[q+QMAX]
    return TOT-p1,p1,p1

def update(w,idx,b,p1,cfg):
    err=(TOT if b else 0)-int(p1);dw=err>>cfg['lr_shift']
    if dw==0:
        if err>0:dw=1
        elif err<0:dw=-1
    for j in idx:
        x=int(w[j])+dw
        if x>WCLIP:x=WCLIP
        elif x<-WCLIP:x=-WCLIP
        w[j]=x

def screen_bits(B,known,bit,cfg):
    w=np.zeros(cfg['dim'],np.int32);bits=0.0
    for t in range(B.shape[1]):
        for c in range(B.shape[0]):
            idx=feat_idx(known,B,bit,c,t,cfg);_,_,p1=model_prob(w,idx,cfg);b=int(B[c,t])
            bits += COST1[p1-1] if b else COST0[p1-1]
            update(w,idx,b,p1,cfg)
    return float(bits)

def neural_encode(B,known,bit,cfgid):
    cfg=CONFIGS[cfgid];w=np.zeros(cfg['dim'],np.int32);ae=rr.ArithEncoder()
    for t in range(B.shape[1]):
        for c in range(B.shape[0]):
            idx=feat_idx(known,B,bit,c,t,cfg);z,o,p1=model_prob(w,idx,cfg);b=int(B[c,t]);ae.encode(b,z,o);update(w,idx,b,p1,cfg)
    araw,nbits=ae.finish();az=m.Z.compress(araw)
    if len(az)<len(araw):am=1;astore=az
    else:am=0;astore=araw
    payload=bytearray([NEURAL_TAG,int(cfgid)]);payload.extend(struct.pack('<BII',am,int(nbits),len(astore)));payload.extend(astore)
    return bytes(payload),{'kind':'online-probability','config':int(cfgid),'dim':cfg['dim'],'lr_shift':cfg['lr_shift'],'score_shift':cfg['score_shift'],'pairs':cfg['pairs'],'arith_bits':int(nbits),'arith_bytes':len(astore),'stored':len(payload)}

def neural_decode(buf,off,known,bit,shape):
    cfgid=int(buf[off]);off+=1;cfg=CONFIGS[cfgid]
    am,nbits,alen=struct.unpack_from('<BII',buf,off);off+=9;astore=buf[off:off+alen];off+=alen
    araw=m.D.decompress(astore) if am else astore;ad=rr.ArithDecoder(araw,nbits);B=np.zeros(shape,np.uint8);w=np.zeros(cfg['dim'],np.int32)
    for t in range(shape[1]):
        for c in range(shape[0]):
            idx=feat_idx(known,B,bit,c,t,cfg);z,o,p1=model_prob(w,idx,cfg);b=ad.decode(z,o);B[c,t]=b;update(w,idx,b,p1,cfg)
    return B,off,cfgid

def best_neural(B,known,bit):
    scr=[(screen_bits(B,known,bit,cfg),i) for i,cfg in enumerate(CONFIGS)];scr.sort()
    best=None
    for ideal,i in scr[:2]:
        payload,d=neural_encode(B,known,bit,i);row=(payload,{**d,'screen_bits':ideal})
        if best is None or len(payload)<len(best[0]):best=row
    return best[0],best[1],{'screen':[[int(i),float(x)] for x,i in scr]}

def super_frame(K):
    K=np.asarray(K,np.int32);z=m.zig(K);mx=int(z.max()) if z.size else 0;nb=max(1,mx.bit_length());known=np.zeros_like(z,np.uint64)
    out=bytearray(struct.pack('<4sHHB',b'HRA3',K.shape[0],K.shape[1],nb));detail=[];floor_len=9
    for bit in range(nb-1,-1,-1):
        B=((z>>bit)&1).astype(np.uint8);best=None
        for fid in range(len(rr.FAMILIES)):
            payload,d=rr.encode_candidate(B,known,bit,fid);row=(payload,{'source':'incumbent-rank',**d})
            if best is None or len(payload)<len(best[0]):best=row
        for afid in range(len(A.ADAPT)):
            payload,d=A.encode_adaptive(B,known,bit,afid);row=(payload,{'source':'incumbent-adaptive',**d})
            if len(payload)<len(best[0]):best=row
        ap,ad,asearch=v7.search_recipe(B,known,bit);arow=(ap,{'source':'auto-recipe',**ad,'search':asearch})
        if len(ap)<len(best[0]):best=arow
        floor_len += len(best[0])
        npay,nd,nsearch=best_neural(B,known,bit);nrow=(npay,{'source':'online-probability',**nd,'search':nsearch})
        if len(npay)<len(best[0]):best=nrow
        payload,d=best;out.extend(payload);detail.append({'bit':bit,'payload_bytes':len(payload),**d});known|=B.astype(np.uint64)<<bit
        print('PLANE',json.dumps({k:v for k,v in detail[-1].items() if k!='search'}),flush=True)
    buf=bytes(out);off=0;magic,nc,nt,nb2=struct.unpack_from('<4sHHB',buf,off);off+=9
    if magic!=b'HRA3' or (nc,nt)!=K.shape or nb2!=nb:raise RuntimeError('header')
    zz=np.zeros_like(z,np.uint64)
    for bit in range(nb-1,-1,-1):
        tag=int(buf[off]);off+=1
        if tag<v7.AUTO_TAG:
            if tag<16:B,off=A.decode_rank_payload(buf,off,zz,bit,tag,K.shape)
            else:
                if tag>=16+len(A.ADAPT):raise RuntimeError(('tag',tag))
                B,off=A.decode_adaptive_payload(buf,off,zz,bit,tag,K.shape)
        elif tag==v7.AUTO_TAG:
            B,off,_=v7.auto_decode(buf,off,zz,bit,K.shape)
        elif tag==NEURAL_TAG:
            B,off,_=neural_decode(buf,off,zz,bit,K.shape)
        else:raise RuntimeError(('unknown tag',tag))
        zz|=B.astype(np.uint64)<<bit
    if off!=len(buf):raise RuntimeError(('trailing',off,len(buf)))
    Kd=m.unzig(zz).astype(np.int32)
    if not np.array_equal(Kd,K):raise RuntimeError('K replay')
    return len(buf),Kd,detail,int(floor_len)

def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std;X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);offs,co,sbest,shist=u.search_sample(X);_,R,K,mb,ob,cod=sbest
    newb,Kd,detail,floorb=super_frame(K)
    Rd=np.zeros(K.shape,np.int32)
    for t in range(K.shape[1]):
        for c in range(K.shape[0]):Rd[c,t]=u.sample_pred(Rd,c,t,cod,offs)+u.STEP*int(Kd[c,t])
    if not np.array_equal(Rd,R):raise RuntimeError('source replay')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('hard',me,eps))
    overhead=fair.COMMON_HEADER+1+len(ob)+len(mb);total=overhead+newb;floor_total=overhead+floorb
    out={'kind':'universal-online-probability-learner-v12','shape':list(X.shape),'eps':eps,'step':u.STEP,'offsets':[list(x) for x in offs],
         'bytes':int(total),'field_bytes':int(newb),'floor_bytes':int(floor_total),'floor_field_bytes':int(floorb),'sz3_bytes':int(szb),'sz3_orientation':ori,
         'gain_vs_sz3':float(szb/total),'gain_vs_floor':float(floor_total/total),'maxerr':me,'planes':detail,'configs':list(CONFIGS),
         'principle':'For each residual bitplane, preserve every existing exact coder as a strict byte floor, then add a decoder-synchronous online nonlinear probability learner. A public hashed categorical feature map converts higher-bit prefixes and causal temporal/spatial bit contexts into a fixed integer weight state. Encoder and decoder update identical integer weights after every decoded bit, so no learned model or probability table is transmitted. Only a one-byte public configuration ID is charged; actual arithmetic payload bytes decide whether the learner is used.'}
    json.dump(out,open('universal_online_probability_learner_v12.json','w'),indent=2);print('FINAL',json.dumps({k:v for k,v in out.items() if k!='planes'},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
