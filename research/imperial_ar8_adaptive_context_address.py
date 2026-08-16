import json,sys,struct
import h5py,numpy as np
import imperial_dyadic_shared_resonator as ar
import imperial_defect_restricted_rank_address as rr
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

P=8
TRAIN=256
STEP=267
HEADER=32
SELECTOR=1
ADAPT=('global','prefix','t','c','tc','prefix_t','prefix_tc','prefix_t2','tc_c4','tc_t8')

def akey(known,B,bit,c,t,fam):
    prefix=int(known[c,t]>>(bit+1))
    pt=int(B[c,t-1]) if t>0 else 2
    pc=int(B[c-1,t]) if c>0 else 2
    pt2=int(B[c,t-2]) if t>1 else 2
    nc,nt=B.shape
    if fam=='global':return 0
    if fam=='prefix':return prefix
    if fam=='t':return pt
    if fam=='c':return pc
    if fam=='tc':return pt*3+pc
    if fam=='prefix_t':return prefix*3+pt
    if fam=='prefix_tc':return prefix*9+pt*3+pc
    if fam=='prefix_t2':return prefix*9+pt*3+pt2
    if fam=='tc_c4':return (c*4//nc)*9+pt*3+pc
    if fam=='tc_t8':return (t*8//nt)*9+pt*3+pc
    raise ValueError(fam)

def encode_adaptive(B,known,bit,afid):
    fam=ADAPT[afid];ae=rr.ArithEncoder();counts={}
    for t in range(B.shape[1]):
        for c in range(B.shape[0]):
            k=akey(known,B,bit,c,t,fam);z,o=counts.get(k,(1,1));b=int(B[c,t]);ae.encode(b,z,o)
            if b:counts[k]=(z,o+1)
            else:counts[k]=(z+1,o)
    araw,nbits=ae.finish();az=m.Z.compress(araw)
    if len(az)<len(araw):am=1;astore=az
    else:am=0;astore=araw
    tag=16+afid
    payload=struct.pack('<BBII',tag,am,int(nbits),len(astore))+astore
    return payload,{'family':'adaptive_'+fam,'groups':len(counts),'arith_bytes':len(astore),'arith_bits':int(nbits),'stored':len(payload),'ones':int(B.sum())}

def decode_rank_payload(buf,off,known,bit,tag,shape):
    cm,am,clen,nbits,alen=struct.unpack_from('<BBIII',buf,off);off+=14
    cstore=buf[off:off+clen];off+=clen;astore=buf[off:off+alen];off+=alen
    craw=m.D.decompress(cstore) if cm else cstore;araw=m.D.decompress(astore) if am else astore
    family=rr.FAMILIES[tag];keys=rr.context_keys(known,bit,family);order,starts,ends=rr.groups_for(keys);ks=[];p=0
    for a,z in zip(starts,ends):
        k,p=rr.get_uvar(craw,p);n=int(z-a)
        if k>n:raise RuntimeError(('count range',bit,k,n))
        ks.append(int(k))
    if p!=len(craw):raise RuntimeError(('count trailing',bit,p,len(craw)))
    ad=rr.ArithDecoder(araw,nbits);sorted_bits=np.empty(shape[0]*shape[1],np.uint8)
    for a,z,k in zip(starts,ends,ks):
        rn=int(z-a);rk=int(k)
        for j in range(int(a),int(z)):
            if rk==0:b=0
            elif rk==rn:b=1
            else:b=ad.decode(rn-rk,rk)
            sorted_bits[j]=b;rn-=1;rk-=b
        if rk:raise RuntimeError(('rank remainder',bit,rk))
    flat=np.empty(shape[0]*shape[1],np.uint8);flat[order]=sorted_bits
    return flat.reshape(shape),off

def decode_adaptive_payload(buf,off,known,bit,tag,shape):
    am,nbits,alen=struct.unpack_from('<BII',buf,off);off+=9
    astore=buf[off:off+alen];off+=alen;araw=m.D.decompress(astore) if am else astore
    afid=tag-16;fam=ADAPT[afid];ad=rr.ArithDecoder(araw,nbits);B=np.zeros(shape,np.uint8);counts={}
    for t in range(shape[1]):
        for c in range(shape[0]):
            k=akey(known,B,bit,c,t,fam);z,o=counts.get(k,(1,1));b=ad.decode(z,o);B[c,t]=b
            if b:counts[k]=(z,o+1)
            else:counts[k]=(z+1,o)
    return B,off

def hybrid_frame(A):
    A=np.asarray(A,np.int32);u=m.zig(A);mx=int(u.max()) if u.size else 0;nb=max(1,mx.bit_length());known=np.zeros_like(u,np.uint64)
    out=bytearray(struct.pack('<4sHHB',b'HRA1',A.shape[0],A.shape[1],nb));detail=[]
    for bit in range(nb-1,-1,-1):
        B=((u>>bit)&1).astype(np.uint8);best=None
        for fid in range(len(rr.FAMILIES)):
            payload,d=rr.encode_candidate(B,known,bit,fid)
            row=(payload,{'kind':'rank',**d})
            if best is None or len(payload)<len(best[0]):best=row
        for afid in range(len(ADAPT)):
            payload,d=encode_adaptive(B,known,bit,afid)
            row=(payload,{'kind':'adaptive',**d})
            if len(payload)<len(best[0]):best=row
        payload,d=best;out.extend(payload);detail.append({'bit':bit,**d});known|=B.astype(np.uint64)<<bit
    buf=bytes(out);off=0;magic,nc,nt,nb2=struct.unpack_from('<4sHHB',buf,off);off+=9
    if magic!=b'HRA1' or (nc,nt)!=A.shape or nb2!=nb:raise RuntimeError('hybrid header')
    uu=np.zeros_like(u,np.uint64)
    for bit in range(nb-1,-1,-1):
        tag=buf[off];off+=1
        if tag<16:B,off=decode_rank_payload(buf,off,uu,bit,tag,A.shape)
        else:
            if tag>=16+len(ADAPT):raise RuntimeError(('tag',tag))
            B,off=decode_adaptive_payload(buf,off,uu,bit,tag,A.shape)
        uu|=B.astype(np.uint64)<<bit
    if off!=len(buf):raise RuntimeError(('trailing',off,len(buf)))
    Ad=m.unzig(uu).astype(np.int32)
    if not np.array_equal(Ad,A):raise RuntimeError('hybrid replay')
    return len(buf),'hybrid_rank_adaptive',Ad,detail

def build_ar8(X,eps):
    co=ar.fit_shared(X[:,:TRAIN],P);mb,cd=ar.model_frame(co);R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):
            pred=ar.predict_hist(R,c,t,cd,P,'shared');k=int(np.rint((float(X[c,t])-pred)/STEP));R[c,t]=pred+STEP*k;K[c,t]=k
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('hard encode',me,eps))
    return int(mb),cd,R,K,me

def replay(X,eps,cd,K,Rref):
    R=np.zeros_like(K)
    for c in range(K.shape[0]):
        for t in range(K.shape[1]):R[c,t]=ar.predict_hist(R,c,t,cd,P,'shared')+STEP*int(K[c,t])
    if not np.array_equal(R,Rref):raise RuntimeError('causal replay')
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('hard replay',me,eps))
    return me

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);old=g.ar32_baseline(X,eps);mb,cd,R,K,me=build_ar8(X,eps)
    rb,_,RK,rd=rr.restricted_rank_frame(K);hb,hn,HK,hd=hybrid_frame(K)
    if not np.array_equal(RK,K) or not np.array_equal(HK,K):raise RuntimeError('K replay')
    mer=replay(X,eps,cd,HK,R)
    rank_total=mb+int(rb)+HEADER+SELECTOR;hybrid_total=mb+int(hb)+HEADER+SELECTOR
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'order':P,'train':TRAIN,'step':STEP,'model_bytes':mb,'rank_floor':{'bytes':rank_total,'payload_bytes':int(rb),'detail':rd},'hybrid':{'bytes':hybrid_total,'payload_bytes':int(hb),'maxerr':mer,'detail':hd,'gain_vs_rank':rank_total/hybrid_total,'gain_vs_old_ar32':old['bytes']/hybrid_total,'gain_vs_sz3':szb/hybrid_total},'old_ar32':old,'sz3':{'bytes':int(szb),'orientation':ori},'adaptive_families':list(ADAPT),'scope':'Exact hybrid constrained address on the PR564 AR8/step267 champion. Existing PR512 combinatorial rank candidates remain available unchanged for every bitplane. In addition, the encoder may choose a causal adaptive arithmetic address whose probability state is generated entirely from decoder-known higher planes plus already decoded same-plane history. Adaptive context counts begin from identical 1/1 priors and are updated deterministically at encoder and decoder, so no per-context counts or learned side model are transmitted. Candidate families include higher-prefix, previous-time/current-channel, previous-channel/current-time, two-neighbor and small coordinate-bucket contexts. Each plane physically stores its selected family tag and arithmetic payload; optional arithmetic-stream Zstd wrapping is charged. The full K field is independently decoded, the charged AR8 model causally regenerates the complete reconstruction, and the unchanged source hard-error bound is verified. Reported bytes are materialized stream bytes only.'}
    json.dump(out,open('imperial_ar8_adaptive_context_address.json','w'),indent=2)
    print(json.dumps({'summary':{'rank_floor':rank_total,'hybrid':hybrid_total,'delta':hybrid_total-rank_total,'old_ar32':old['bytes'],'sz3':int(szb),'gain_vs_rank':rank_total/hybrid_total,'gain_vs_old_ar32':old['bytes']/hybrid_total,'gain_vs_sz3':szb/hybrid_total}},indent=2),flush=True)
    for x in hd:print(json.dumps(x),flush=True)

if __name__=='__main__':main(sys.argv[1])
