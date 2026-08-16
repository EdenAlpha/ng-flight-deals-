import json,sys,struct
import h5py,numpy as np
import imperial_dyadic_shared_resonator as ar
import imperial_defect_restricted_rank_address as rr
import imperial_decoder_phase_automaton as m

T0=14488
C0=512
C=128
T=1024
TRAIN=256
STEP=267
ORDERS=(8,12,16)
GLOBAL_HEADER=32
SELECTOR=1
ADAPT_FAMILIES=('local2','local3','prefix2_local2','prefix3_local2','prefixnz_local3','c4_local2','t4_local2','highneigh_local2','prefix2_local3')


def ctx_id(fam,known,B,bit,c,t):
    nc,nt=B.shape
    l=int(B[c-1,t]) if c>0 else 0
    u=int(B[c,t-1]) if t>0 else 0
    d=int(B[c-1,t-1]) if c>0 and t>0 else 0
    local2=(l<<1)|u;local3=(l<<2)|(u<<1)|d
    p=int(known[c,t]>>(bit+1))
    if fam==0:return local2,4
    if fam==1:return local3,8
    if fam==2:return ((p&3)<<2)|local2,16
    if fam==3:return ((p&7)<<2)|local2,32
    if fam==4:return ((1 if p else 0)<<3)|local3,16
    if fam==5:return ((c*4//nc)<<2)|local2,16
    if fam==6:return ((t&3)<<2)|local2,16
    if fam==7:
        ph=p&1
        pl=(int(known[c-1,t]>>(bit+1))&1) if c>0 else 0
        pu=(int(known[c,t-1]>>(bit+1))&1) if t>0 else 0
        return (ph<<4)|(pl<<3)|(pu<<2)|local2,32
    if fam==8:return ((p&3)<<3)|local3,32
    raise ValueError(fam)


def encode_adaptive(B,known,bit,fam):
    # public deterministic contexts, adaptive Laplace counts; no count table is transmitted.
    _,nctx=ctx_id(fam,known,B,bit,0,0);cnt=np.ones((nctx,2),np.int64);ae=rr.ArithEncoder()
    for t in range(B.shape[1]):
        for c in range(B.shape[0]):
            q,_=ctx_id(fam,known,B,bit,c,t);b=int(B[c,t]);ae.encode(b,int(cnt[q,0]),int(cnt[q,1]));cnt[q,b]+=1
    araw,nbits=ae.finish();az=m.Z.compress(araw)
    if len(az)<len(araw):am=1;store=az
    else:am=0;store=araw
    payload=struct.pack('<BBII',fam,am,int(nbits),len(store))+store
    return payload,{'family':ADAPT_FAMILIES[fam],'adaptive_contexts':nctx,'arith_bits':int(nbits),'arith_bytes':len(store),'stored':len(payload)}


def decode_adaptive(payload,known,bit,shape):
    fam,am,nbits,L=struct.unpack_from('<BBII',payload,0);store=payload[10:10+L]
    if len(payload)!=10+L:raise RuntimeError('adaptive payload trailing')
    araw=m.D.decompress(store) if am else store;ad=rr.ArithDecoder(araw,nbits);B=np.zeros(shape,np.uint8)
    _,nctx=ctx_id(fam,known,B,bit,0,0);cnt=np.ones((nctx,2),np.int64)
    for t in range(shape[1]):
        for c in range(shape[0]):
            q,_=ctx_id(fam,known,B,bit,c,t);b=ad.decode(int(cnt[q,0]),int(cnt[q,1]));B[c,t]=b;cnt[q,b]+=1
    return B


def decode_rank_payload(payload,known,bit,shape):
    off=0;fid,cm,am,clen,nbits,alen=struct.unpack_from('<BBBIII',payload,off);off+=15
    cstore=payload[off:off+clen];off+=clen;astore=payload[off:off+alen];off+=alen
    if off!=len(payload):raise RuntimeError('rank payload trailing')
    craw=m.D.decompress(cstore) if cm else cstore;araw=m.D.decompress(astore) if am else astore
    keys=rr.context_keys(known,bit,rr.FAMILIES[fid]);order,starts,ends=rr.groups_for(keys);ks=[];p=0
    for a,z in zip(starts,ends):
        k,p=rr.get_uvar(craw,p);n=int(z-a)
        if k>n:raise RuntimeError(('rank count',k,n));ks.append(int(k))
        ks.append(int(k)) if False else None
    if len(ks)!=len(starts):
        # previous compact branch above only appends through this explicit path
        ks=[];p=0
        for a,z in zip(starts,ends):
            k,p=rr.get_uvar(craw,p);n=int(z-a)
            if k>n:raise RuntimeError(('rank count',k,n))
            ks.append(int(k))
    if p!=len(craw):raise RuntimeError('rank count trailing')
    ad=rr.ArithDecoder(araw,nbits);sorted_bits=np.empty(np.prod(shape),np.uint8)
    for a,z,k in zip(starts,ends,ks):
        rn=int(z-a);rk=int(k)
        for j in range(int(a),int(z)):
            if rk==0:b=0
            elif rk==rn:b=1
            else:b=ad.decode(rn-rk,rk)
            sorted_bits[j]=b;rn-=1;rk-=b
        if rk:raise RuntimeError('rank remainder')
    flat=np.empty(np.prod(shape),np.uint8);flat[order]=sorted_bits
    return flat.reshape(shape)


def portfolio_frame(K):
    A=np.asarray(K,np.int32);u=m.zig(A);mx=int(u.max()) if u.size else 0;nb=max(1,mx.bit_length());known=np.zeros_like(u,np.uint64)
    out=bytearray(struct.pack('<4sHHB',b'AGP1',A.shape[0],A.shape[1],nb));detail=[]
    for bit in range(nb-1,-1,-1):
        B=((u>>bit)&1).astype(np.uint8)
        rawz=m.Z.compress(np.packbits(B.ravel(),bitorder='little').tobytes());best=(bytes([0])+struct.pack('<I',len(rawz))+rawz,{'mode':'raw','family':'raw_zstd'})
        for fid in range(len(rr.FAMILIES)):
            p,d=rr.encode_candidate(B,known,bit,fid);entry=bytes([1])+p
            if len(entry)<len(best[0]):best=(entry,{'mode':'rank',**d})
        for fam in range(len(ADAPT_FAMILIES)):
            p,d=encode_adaptive(B,known,bit,fam);entry=bytes([2])+p
            if len(entry)<len(best[0]):best=(entry,{'mode':'adaptive',**d})
        entry,d=best;out.extend(entry);detail.append({'bit':bit,'stored':len(entry),**d});known|=B.astype(np.uint64)<<bit
    buf=bytes(out);magic,nc,nt,nb2=struct.unpack_from('<4sHHB',buf,0);off=9
    if magic!=b'AGP1' or (nc,nt)!=A.shape or nb2!=nb:raise RuntimeError('portfolio head')
    uu=np.zeros_like(u,np.uint64)
    for bit in range(nb-1,-1,-1):
        mode=buf[off];off+=1
        if mode==0:
            L=struct.unpack_from('<I',buf,off)[0];off+=4;store=buf[off:off+L];off+=L
            raw=m.D.decompress(store);B=np.unpackbits(np.frombuffer(raw,np.uint8),bitorder='little')[:A.size].astype(np.uint8).reshape(A.shape)
        elif mode==1:
            fid,cm,am,clen,nbits,alen=struct.unpack_from('<BBBIII',buf,off);L=15+clen+alen;payload=buf[off:off+L];off+=L;B=decode_rank_payload(payload,uu,bit,A.shape)
        elif mode==2:
            fam,am,nbits,L=struct.unpack_from('<BBII',buf,off);tot=10+L;payload=buf[off:off+tot];off+=tot;B=decode_adaptive(payload,uu,bit,A.shape)
        else:raise RuntimeError(('mode',mode))
        uu|=B.astype(np.uint64)<<bit
    if off!=len(buf):raise RuntimeError(('portfolio trailing',off,len(buf)))
    Ad=m.unzig(uu).astype(np.int32)
    if not np.array_equal(Ad,A):raise RuntimeError('portfolio replay')
    return len(buf),'adaptive_gps_plane_portfolio',Ad,detail


def build(X,eps,p):
    co=ar.fit_shared(X[:,:TRAIN],p);mb,coef=ar.model_frame(co);R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):
            pr=ar.predict_hist(R,c,t,coef,p,'shared');k=int(np.rint((float(X[c,t])-pr)/STEP));R[c,t]=pr+STEP*k;K[c,t]=k
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('hard build',p,me))
    return int(mb),coef,R,K,me


def replay(X,eps,p,coef,K,Rref):
    R=np.zeros(K.shape,np.int32)
    for c in range(K.shape[0]):
        for t in range(K.shape[1]):R[c,t]=ar.predict_hist(R,c,t,coef,p,'shared')+STEP*int(K[c,t])
    if not np.array_equal(R,Rref):raise RuntimeError(('causal replay',p))
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('hard replay',p,me))
    return me


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[T0:T0+T,C0:C0+C],np.float64).T
    szb,ori=m.szrun(X,eps);rows=[]
    for p in ORDERS:
        mb,coef,R,K,me=build(X,eps,p);legacy=m.encode_k(K);pb,pn,Kd,detail=portfolio_frame(K)
        for rep,n,Q,det in ((legacy[1],int(legacy[0]),np.asarray(legacy[2],np.int32),None),(pn,int(pb),np.asarray(Kd,np.int32),detail)):
            mer=replay(X,eps,p,coef,Q,R);total=mb+n+GLOBAL_HEADER+SELECTOR
            row={'order':p,'rep':rep,'bytes':total,'bps':8*total/X.size,'model_bytes':mb,'payload_bytes':n,'maxerr':mer,'gain_vs_sz3':szb/total,'detail':det};rows.append(row);print(json.dumps({k:v for k,v in row.items() if k!='detail'},indent=2),flush=True)
    rows.sort(key=lambda r:r['bytes']);best=rows[0]
    out={'region':'hard','shape':[C,T],'global_std':std,'eps':eps,'step':STEP,'train':TRAIN,'orders':list(ORDERS),'adaptive_families':list(ADAPT_FAMILIES),'sz3':{'bytes':int(szb),'orientation':ori},'rows':rows,'best':best,'scope':'Decoder-real Adaptive-GPS bitplane portfolio on fixed hard 128x1024 Imperial. The AR reconstruction and K field are fixed per charged public order. Each zigzag K plane is decoded MSB-first and stores the smallest actual stream among raw packed-bit Zstd, exact PR512 restricted/enumerative ranking, and a family of causal adaptive binary decision-tree arithmetic coders. Adaptive contexts use only already decoded higher-plane state, already decoded same-plane spatial/time neighbors, and public coordinates. Laplace counts start at 1/1 and update identically at encoder and decoder, so no probability/count table is transmitted. Every per-plane mode/family selector and all payload framing are physically charged. Final K is byte-exact, the charged AR model causally replays the identical reconstruction, and the unchanged source hard-error bound is verified.'}
    json.dump(out,open('imperial_hard_adaptive_gps_plane_address.json','w'),indent=2)
    print(json.dumps({'summary':{'best_order':best['order'],'best_rep':best['rep'],'best_bytes':best['bytes'],'sz3':int(szb),'gain_vs_sz3':szb/best['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
