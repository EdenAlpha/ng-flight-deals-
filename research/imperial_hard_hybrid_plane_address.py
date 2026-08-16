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
ORDERS=(4,8,12,14,16,18,20)
GLOBAL_HEADER=32
SELECTOR=1


def decode_rank_payload(payload,known,bit,shape):
    off=0
    fid,cm,am,clen,nbits,alen=struct.unpack_from('<BBBIII',payload,off);off+=15
    cstore=payload[off:off+clen];off+=clen;astore=payload[off:off+alen];off+=alen
    if off!=len(payload):raise RuntimeError(('rank payload trailing',off,len(payload)))
    craw=m.D.decompress(cstore) if cm else cstore;araw=m.D.decompress(astore) if am else astore
    keys=rr.context_keys(known,bit,rr.FAMILIES[fid]);order,starts,ends=rr.groups_for(keys);ks=[];p=0
    for a,z in zip(starts,ends):
        k,p=rr.get_uvar(craw,p);n=int(z-a)
        if k>n:raise RuntimeError(('count range',bit,k,n))
        ks.append(int(k))
    if p!=len(craw):raise RuntimeError(('count trailing',bit,p,len(craw)))
    ad=rr.ArithDecoder(araw,nbits);sorted_bits=np.empty(np.prod(shape),np.uint8)
    for a,z,k in zip(starts,ends,ks):
        rn=int(z-a);rk=int(k)
        for j in range(int(a),int(z)):
            if rk==0:b=0
            elif rk==rn:b=1
            else:b=ad.decode(rn-rk,rk)
            sorted_bits[j]=b;rn-=1;rk-=b
        if rk!=0:raise RuntimeError(('rank remainder',bit,rk))
    Bflat=np.empty(np.prod(shape),np.uint8);Bflat[order]=sorted_bits
    return Bflat.reshape(shape)


def hybrid_frame(K):
    A=np.asarray(K,np.int32);u=m.zig(A);mx=int(u.max()) if u.size else 0;nb=max(1,mx.bit_length());known=np.zeros_like(u,np.uint64)
    out=bytearray(struct.pack('<4sHHB',b'HPA1',A.shape[0],A.shape[1],nb));detail=[]
    for bit in range(nb-1,-1,-1):
        B=((u>>bit)&1).astype(np.uint8)
        packed=np.packbits(B.ravel(),bitorder='little').tobytes();rz=m.Z.compress(packed)
        raw=bytes([0])+struct.pack('<I',len(rz))+rz
        rbest=None
        for fid in range(len(rr.FAMILIES)):
            payload,d=rr.encode_candidate(B,known,bit,fid);entry=bytes([1])+payload
            if rbest is None or len(entry)<len(rbest[0]):rbest=(entry,d)
        if len(raw)<=len(rbest[0]):
            entry=raw;d={'family':'raw_zstd','groups':0,'count_bytes':0,'arith_bytes':0,'arith_bits':0,'ones':int(B.sum()),'stored':len(entry),'mode':'raw'}
        else:
            entry,d=rbest;d={**d,'stored':len(entry),'mode':'rank'}
        out.extend(entry);detail.append({'bit':bit,**d,'raw_candidate_bytes':len(raw),'rank_candidate_bytes':len(rbest[0])});known|=B.astype(np.uint64)<<bit
    buf=bytes(out);off=0;magic,nc,nt,nb2=struct.unpack_from('<4sHHB',buf,off);off+=9
    if magic!=b'HPA1' or (nc,nt)!=A.shape or nb2!=nb:raise RuntimeError('hybrid header')
    uu=np.zeros_like(u,np.uint64)
    for bit in range(nb-1,-1,-1):
        mode=buf[off];off+=1
        if mode==0:
            L=struct.unpack_from('<I',buf,off)[0];off+=4;bb=buf[off:off+L];off+=L
            raw=m.D.decompress(bb);bits=np.unpackbits(np.frombuffer(raw,np.uint8),bitorder='little')[:A.size].astype(np.uint8);B=bits.reshape(A.shape)
        elif mode==1:
            if off+15>len(buf):raise RuntimeError('rank head eof')
            fid,cm,am,clen,nbits,alen=struct.unpack_from('<BBBIII',buf,off);L=15+clen+alen;payload=buf[off:off+L];off+=L
            B=decode_rank_payload(payload,uu,bit,A.shape)
        else:raise RuntimeError(('bad mode',mode))
        uu|=B.astype(np.uint64)<<bit
    if off!=len(buf):raise RuntimeError(('hybrid trailing',off,len(buf)))
    Ad=m.unzig(uu).astype(np.int32)
    if not np.array_equal(Ad,A):raise RuntimeError('hybrid replay')
    return len(buf),'hybrid_plane_address',Ad,detail


def build(X,eps,p):
    co=ar.fit_shared(X[:,:TRAIN],p);mb,coef=ar.model_frame(co);R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):
            pred=ar.predict_hist(R,c,t,coef,p,'shared');k=int(np.rint((float(X[c,t])-pred)/STEP));R[c,t]=pred+STEP*k;K[c,t]=k
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('hard encode',p,me,eps))
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
        mb,coef,R,K,me=build(X,eps,p)
        legacy=m.encode_k(K);rb,rn,RK,rd=rr.restricted_rank_frame(K);hb,hn,HK,hd=hybrid_frame(K)
        for name,pb,Kd,detail in ((legacy[1],int(legacy[0]),np.asarray(legacy[2],np.int32),None),(rn,int(rb),np.asarray(RK,np.int32),rd),(hn,int(hb),np.asarray(HK,np.int32),hd)):
            mer=replay(X,eps,p,coef,Kd,R);total=mb+pb+GLOBAL_HEADER+SELECTOR
            r={'order':p,'rep':name,'bytes':total,'bps':8*total/X.size,'model_bytes':mb,'payload_bytes':pb,'header_bytes':GLOBAL_HEADER,'selector_bytes':SELECTOR,'maxerr':mer,'gain_vs_sz3':szb/total,'detail':detail};rows.append(r)
            print(json.dumps({k:v for k,v in r.items() if k!='detail'},indent=2),flush=True)
    rows.sort(key=lambda r:r['bytes']);best=rows[0]
    out={'region':'hard','shape':[C,T],'t0':T0,'c0':C0,'global_std':std,'eps':eps,'step':STEP,'train':TRAIN,'orders':list(ORDERS),'sz3':{'bytes':int(szb),'orientation':ori},'rows':rows,'best':best,'scope':'Exact per-bitplane address-language portfolio on the fixed hard 128x1024 Imperial object. For each shared AR order, the causal reconstruction and K field are fixed. Each zigzag K bitplane is decoded MSB-first and independently chooses the smaller real serialized representation between (a) PR512 decoder-known restricted/enumerative ranking and (b) direct packed-bit Zstd. A one-byte per-plane mode marker and all representation-specific framing are physically present in the stream. Rank planes remain conditioned only on already decoded higher planes/public coordinates; raw planes simply decode their exact bits. The full K field is reconstructed byte-exact, then the charged AR model causally replays the identical reconstruction and the unchanged source hard-error bound is verified. This directly prevents near-random low planes from paying enumerative overhead while retaining restricted-address gains on structured upper planes.'}
    json.dump(out,open('imperial_hard_hybrid_plane_address.json','w'),indent=2)
    print(json.dumps({'summary':{'best_order':best['order'],'best_rep':best['rep'],'best_bytes':best['bytes'],'sz3':int(szb),'gain_vs_sz3':szb/best['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
