import sys,json,struct,math
import h5py,numpy as np
import imperial_ar4_rich_adaptive_context_address as rich
import imperial_defect_restricted_rank_address as rr
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

a=rich.a
a.P=1
a.TRAIN=64
HEADER=32
SELECTOR=1
SIGNF=('global','mag','magbin','t','c','tc','mag_tc','magbin_tc','magpar_tc')

def sign_key(M,S,c,t,fam):
    mag=int(M[c,t]);mb=max(0,mag.bit_length()-1)
    pt=int(S[c,t-1]) if t>0 and M[c,t-1]!=0 else 2
    pc=int(S[c-1,t]) if c>0 and M[c-1,t]!=0 else 2
    if fam=='global':return 0
    if fam=='mag':return mag
    if fam=='magbin':return mb
    if fam=='t':return pt
    if fam=='c':return pc
    if fam=='tc':return pt*3+pc
    if fam=='mag_tc':return (mag,pt,pc)
    if fam=='magbin_tc':return (mb,pt,pc)
    if fam=='magpar_tc':return (mag&1,mb,pt,pc)
    raise ValueError(fam)

def encode_sign(M,S,fid):
    fam=SIGNF[fid];counts={};ae=rr.ArithEncoder();n=0;ones=0
    for t in range(M.shape[1]):
        for c in range(M.shape[0]):
            if M[c,t]==0:continue
            k=sign_key(M,S,c,t,fam);z,o=counts.get(k,(1,1));b=int(S[c,t]);ae.encode(b,z,o);n+=1;ones+=b
            counts[k]=(z,o+1) if b else (z+1,o)
    araw,nbits=ae.finish();az=m.Z.compress(araw)
    if len(az)<len(araw):am=1;astore=az
    else:am=0;astore=araw
    payload=struct.pack('<BBII',fid,am,int(nbits),len(astore))+astore
    return payload,{'family':fam,'coded_nonzero':n,'negative':ones,'groups':len(counts),'arith_bits':int(nbits),'arith_bytes':len(astore),'stored':len(payload)}

def decode_sign(buf,off,M):
    fid,am,nbits,alen=struct.unpack_from('<BBII',buf,off);off+=10
    if fid>=len(SIGNF):raise RuntimeError(('sign fid',fid))
    astore=buf[off:off+alen];off+=alen;araw=m.D.decompress(astore) if am else astore
    fam=SIGNF[fid];counts={};ad=rr.ArithDecoder(araw,nbits);S=np.zeros(M.shape,np.uint8)
    for t in range(M.shape[1]):
        for c in range(M.shape[0]):
            if M[c,t]==0:continue
            k=sign_key(M,S,c,t,fam);z,o=counts.get(k,(1,1));b=ad.decode(z,o);S[c,t]=b
            counts[k]=(z,o+1) if b else (z+1,o)
    return S,off

def mag_sign_frame(K):
    K=np.asarray(K,np.int32);M=np.abs(K.astype(np.int64)).astype(np.uint64);S=(K<0).astype(np.uint8)
    mx=int(M.max()) if M.size else 0;nb=max(1,mx.bit_length());known=np.zeros_like(M,np.uint64)
    out=bytearray(struct.pack('<4sHHB',b'MSA1',K.shape[0],K.shape[1],nb));detail=[]
    for bit in range(nb-1,-1,-1):
        B=((M>>bit)&1).astype(np.uint8);best=None
        for fid in range(len(rr.FAMILIES)):
            payload,d=rr.encode_candidate(B,known,bit,fid);row=(payload,{'kind':'rank',**d})
            if best is None or len(payload)<len(best[0]):best=row
        for afid in range(len(a.ADAPT)):
            payload,d=a.encode_adaptive(B,known,bit,afid);row=(payload,{'kind':'adaptive',**d})
            if len(payload)<len(best[0]):best=row
        payload,d=best;out.extend(payload);detail.append({'magnitude_bit':bit,**d});known|=B.astype(np.uint64)<<bit
    sbest=None
    for fid in range(len(SIGNF)):
        payload,d=encode_sign(M,S,fid);row=(payload,d)
        if sbest is None or len(payload)<len(sbest[0]):sbest=row
    out.extend(sbest[0]);sdetail=sbest[1]
    buf=bytes(out);off=0;magic,nc,nt,nb2=struct.unpack_from('<4sHHB',buf,off);off+=9
    if magic!=b'MSA1' or (nc,nt)!=K.shape or nb2!=nb:raise RuntimeError('mag-sign header')
    Md=np.zeros_like(M,np.uint64)
    for bit in range(nb-1,-1,-1):
        tag=buf[off];off+=1
        if tag<16:B,off=a.decode_rank_payload(buf,off,Md,bit,tag,K.shape)
        else:
            if tag>=16+len(a.ADAPT):raise RuntimeError(('mag tag',tag))
            B,off=a.decode_adaptive_payload(buf,off,Md,bit,tag,K.shape)
        Md|=B.astype(np.uint64)<<bit
    Sd,off=decode_sign(buf,off,Md)
    if off!=len(buf):raise RuntimeError(('trailing',off,len(buf)))
    Kd=Md.astype(np.int64);Kd=np.where(Sd!=0,-Kd,Kd).astype(np.int32)
    if not np.array_equal(Kd,K):raise RuntimeError('mag-sign K replay')
    return len(buf),'magnitude_sign',Kd,{'magnitude':detail,'sign':sdetail,'magnitude_bits':nb}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);old=g.ar32_baseline(X,eps);mb,cd,R,K,me=a.build_ar8(X,eps)
    zb,zn,ZK,zd=a.hybrid_frame(K);msb,msn,MSK,msd=mag_sign_frame(K)
    if not np.array_equal(ZK,K) or not np.array_equal(MSK,K):raise RuntimeError('K replay')
    zme=a.replay(X,eps,cd,ZK,R);msme=a.replay(X,eps,cd,MSK,R)
    ztotal=int(mb)+int(zb)+HEADER+SELECTOR;mstotal=int(mb)+int(msb)+HEADER+SELECTOR
    chosen='magnitude_sign' if mstotal<ztotal else 'zigzag_rich';best=min(ztotal,mstotal)
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'order':1,'train':64,'step':267,'model_bytes':int(mb),'zigzag_rich':{'bytes':ztotal,'payload_bytes':int(zb),'maxerr':zme,'detail':zd},'magnitude_sign':{'bytes':mstotal,'payload_bytes':int(msb),'maxerr':msme,'detail':msd},'chosen':chosen,'best_bytes':best,'delta_magnitude_sign_vs_zigzag':mstotal-ztotal,'old_ar32':old,'sz3':{'bytes':int(szb),'orientation':ori},'gain_vs_old_ar32':old['bytes']/best,'gain_vs_sz3':szb/best,'scope':'Decoder-real coordinate-representation test on AR1/train64/step267. The proven richer zigzag address is reproduced as a strict floor. The alternative maps K bijectively to exact magnitude plus sign. Magnitude is encoded first with the same exact rank/adaptive context competition but without zigzag sign-dependent decrement; once magnitude is decoded, zero positions are known and sign is arithmetic-coded only on nonzero entries using a small public family of magnitude and causal sign contexts. The selected sign family is physically stored; no probability table is transmitted. The complete K field is independently reconstructed, AR1 is causally replayed, and the unchanged source hard-error bound is verified.'}
    json.dump(out,open('imperial_ar1_magnitude_sign_address.json','w'),indent=2)
    print(json.dumps({'summary':{'zigzag_rich':ztotal,'magnitude_sign':mstotal,'delta':mstotal-ztotal,'chosen':chosen,'best':best,'old_ar32':old['bytes'],'sz3':int(szb),'gain_vs_old_ar32':old['bytes']/best,'gain_vs_sz3':szb/best,'sign':msd['sign']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
