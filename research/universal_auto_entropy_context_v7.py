#!/usr/bin/env python3
from __future__ import annotations
import json,struct,sys
import h5py,numpy as np
import universal_rate_searched_predictor_v1 as u
import imperial_defect_restricted_rank_address as rr
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m
import imperial_fair_ar_coarse_prefix_container as fair

A=u.A
V1_BYTES=22390
AUTO_TAG=240
MAX_DEPTH=5
TOP_SINGLE=8

# Generic decoder-known primitive IDs. No seismic-specific names are encoded.
PRIMS=(0,1,2,3,10,11,12,13,14,15,20,21,22,23,30,31,32,33,34,35,36,37,40,41,42,43,44,45,50,51,60,61,62)


def at_bit(B,c,t,dc,dt):
    cc=c+dc;tt=t-dt
    if cc<0 or cc>=B.shape[0] or tt<0:return 2
    if dt==0 and dc>=0:return 2
    return int(B[cc,tt])


def hp(known,bit,c,t,dc=0,dt=0,skip=0):
    cc=c+dc;tt=t-dt
    if cc<0 or cc>=known.shape[0] or tt<0:return -1
    return int(known[cc,tt]>>(bit+1+skip))


def pval(code,known,B,bit,c,t):
    if code in (0,1,2,3):return hp(known,bit,c,t,skip=code)
    if 10<=code<=15:
        lag=(1,2,4,6,8,16)[code-10];return at_bit(B,c,t,0,lag)
    if 20<=code<=23:
        dc=(1,2,4,8)[code-20];return at_bit(B,c,t,-dc,0)
    if code==30:return at_bit(B,c,t,-1,1)
    if code==31:return at_bit(B,c,t,1,1)
    if code==32:return at_bit(B,c,t,-1,2)
    if code==33:return at_bit(B,c,t,1,2)
    if code==34:return at_bit(B,c,t,-1,6)
    if code==35:return at_bit(B,c,t,1,6)
    if code==36:return at_bit(B,c,t,-1,16)
    if code==37:return at_bit(B,c,t,1,16)
    if code==40:return hp(known,bit,c,t,0,1)
    if code==41:return hp(known,bit,c,t,-1,0)
    if code==42:return hp(known,bit,c,t,-1,1)
    if code==43:return hp(known,bit,c,t,1,1)
    if code==44:return hp(known,bit,c,t,0,6)
    if code==45:return hp(known,bit,c,t,0,16)
    if code==50:return t*4//B.shape[1]
    if code==51:return c*4//B.shape[0]
    if code==60:
        a=hp(known,bit,c,t);b=hp(known,bit,c,t,0,1);return min(7,abs(a-b)) if b>=0 else 8
    if code==61:
        a=hp(known,bit,c,t);b=hp(known,bit,c,t,-1,0);return min(7,abs(a-b)) if b>=0 else 8
    if code==62:
        a=hp(known,bit,c,t,-1,1);b=hp(known,bit,c,t,1,1);return min(7,abs(a-b)) if a>=0 and b>=0 else 8
    raise ValueError(code)


def auto_encode(B,known,bit,recipe):
    ae=rr.ArithEncoder();counts={}
    for t in range(B.shape[1]):
        for c in range(B.shape[0]):
            key=tuple(pval(q,known,B,bit,c,t) for q in recipe) if recipe else 0
            z,o=counts.get(key,(1,1));b=int(B[c,t]);ae.encode(b,z,o)
            counts[key]=(z,o+1) if b else (z+1,o)
    araw,nbits=ae.finish();az=m.Z.compress(araw)
    if len(az)<len(araw):am=1;astore=az
    else:am=0;astore=araw
    payload=bytearray([AUTO_TAG,len(recipe),*recipe]);payload.extend(struct.pack('<BII',am,int(nbits),len(astore)));payload.extend(astore)
    return bytes(payload),{'kind':'auto','recipe':list(recipe),'groups':len(counts),'arith_bits':int(nbits),'arith_bytes':len(astore),'stored':len(payload)}


def auto_decode(buf,off,known,bit,shape):
    n=int(buf[off]);off+=1;recipe=tuple(int(x) for x in buf[off:off+n]);off+=n
    am,nbits,alen=struct.unpack_from('<BII',buf,off);off+=9;astore=buf[off:off+alen];off+=alen
    araw=m.D.decompress(astore) if am else astore;ad=rr.ArithDecoder(araw,nbits);B=np.zeros(shape,np.uint8);counts={}
    for t in range(shape[1]):
        for c in range(shape[0]):
            key=tuple(pval(q,known,B,bit,c,t) for q in recipe) if recipe else 0
            z,o=counts.get(key,(1,1));b=ad.decode(z,o);B[c,t]=b;counts[key]=(z,o+1) if b else (z+1,o)
    return B,off,recipe


def search_recipe(B,known,bit):
    cache={}
    def enc(r):
        r=tuple(r)
        if r not in cache:cache[r]=auto_encode(B,known,bit,r)
        return cache[r]
    base=enc(())
    singles=[]
    for p in PRIMS:
        q=enc((p,));singles.append((len(q[0]),p,q))
    singles.sort(key=lambda x:x[0]);seeds=singles[:TOP_SINGLE]
    best=(len(base[0]),(),base)
    if seeds and seeds[0][0]<best[0]:best=(seeds[0][0],(seeds[0][1],),seeds[0][2])
    # Pair lookahead among the strongest singleton primitives.
    for i in range(len(seeds)):
        for j in range(i+1,len(seeds)):
            r=(seeds[i][1],seeds[j][1]);q=enc(r)
            if len(q[0])<best[0]:best=(len(q[0]),r,q)
    # Greedy continuation from the strongest current recipe.
    while len(best[1])<MAX_DEPTH:
        winner=best
        for p in PRIMS:
            if p in best[1]:continue
            r=best[1]+(p,);q=enc(r)
            if len(q[0])<winner[0]:winner=(len(q[0]),r,q)
        if winner[0]>=best[0]:break
        best=winner
    return best[2][0],best[2][1],{'tested_recipes':len(cache),'best_recipe':list(best[1]),'best_bytes':best[0],'global_bytes':len(base[0]),'top_singletons':[[int(p),int(n)] for n,p,_ in seeds]}


def super_frame(K):
    K=np.asarray(K,np.int32);z=m.zig(K);mx=int(z.max()) if z.size else 0;nb=max(1,mx.bit_length());known=np.zeros_like(z,np.uint64)
    out=bytearray(struct.pack('<4sHHB',b'HRA2',K.shape[0],K.shape[1],nb));detail=[]
    for bit in range(nb-1,-1,-1):
        B=((z>>bit)&1).astype(np.uint8);best=None
        # Exact incumbent candidate set.
        for fid in range(len(rr.FAMILIES)):
            payload,d=rr.encode_candidate(B,known,bit,fid);row=(payload,{'source':'incumbent-rank',**d})
            if best is None or len(payload)<len(best[0]):best=row
        for afid in range(len(A.ADAPT)):
            payload,d=A.encode_adaptive(B,known,bit,afid);row=(payload,{'source':'incumbent-adaptive',**d})
            if len(payload)<len(best[0]):best=row
        # Automatically discovered recipe is an additional candidate, never a replacement floor.
        ap,ad,search=search_recipe(B,known,bit);arow=(ap,{'source':'auto-recipe',**ad,'search':search})
        if len(ap)<len(best[0]):best=arow
        payload,d=best;out.extend(payload);detail.append({'bit':bit,'payload_bytes':len(payload),**d});known|=B.astype(np.uint64)<<bit
        print('PLANE',json.dumps({k:v for k,v in detail[-1].items() if k!='search'}),flush=True)
    buf=bytes(out);off=0;magic,nc,nt,nb2=struct.unpack_from('<4sHHB',buf,off);off+=9
    if magic!=b'HRA2' or (nc,nt)!=K.shape or nb2!=nb:raise RuntimeError('header')
    zz=np.zeros_like(z,np.uint64)
    for bit in range(nb-1,-1,-1):
        tag=int(buf[off]);off+=1
        if tag<AUTO_TAG:
            if tag<16:B,off=A.decode_rank_payload(buf,off,zz,bit,tag,K.shape)
            else:
                if tag>=16+len(A.ADAPT):raise RuntimeError(('tag',tag))
                B,off=A.decode_adaptive_payload(buf,off,zz,bit,tag,K.shape)
        else:
            if tag!=AUTO_TAG:raise RuntimeError(('auto tag',tag))
            B,off,_=auto_decode(buf,off,zz,bit,K.shape)
        zz|=B.astype(np.uint64)<<bit
    if off!=len(buf):raise RuntimeError(('trailing',off,len(buf)))
    Kd=m.unzig(zz).astype(np.int32)
    if not np.array_equal(Kd,K):raise RuntimeError('K replay')
    return len(buf),Kd,detail


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std;X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps)
    offs,co,sbest,shist=u.search_sample(X);_,R,K,mb,ob,cod=sbest
    incumbent,_,_=u.exact_field(K);newb,Kd,detail=super_frame(K)
    Rd=np.zeros(K.shape,np.int32)
    for t in range(K.shape[1]):
        for c in range(K.shape[0]):Rd[c,t]=u.sample_pred(Rd,c,t,cod,offs)+u.STEP*int(Kd[c,t])
    if not np.array_equal(Rd,R):raise RuntimeError('source replay')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('hard',me,eps))
    total=fair.COMMON_HEADER+1+len(ob)+len(mb)+newb
    out={'kind':'universal-auto-entropy-context-v7','shape':list(X.shape),'eps':eps,'step':u.STEP,'offsets':[list(x) for x in offs],
         'bytes':int(total),'field_bytes':int(newb),'incumbent_field_bytes':int(incumbent),'v1_bytes':V1_BYTES,'sz3_bytes':int(szb),'sz3_orientation':ori,
         'gain_vs_sz3':float(szb/total),'gain_vs_v1':float(V1_BYTES/total),'maxerr':me,'planes':detail,
         'principle':'Preserve the exact incumbent rank/adaptive/mixture entropy candidates as a per-bitplane floor, then let the codec search a generic grammar of decoder-known causal relationships and add the best discovered context recipe as another candidate. Recipe IDs are physically serialized; probabilities adapt online from identical 1/1 priors, so no probability tables are transmitted.'}
    json.dump(out,open('universal_auto_entropy_context_v7.json','w'),indent=2)
    print('FINAL',json.dumps({k:v for k,v in out.items() if k!='planes'},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
