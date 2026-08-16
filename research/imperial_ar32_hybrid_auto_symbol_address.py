import json,sys,struct
import h5py,numpy as np
import imperial_ar32_autocomplexity_address as base
import imperial_defect_restricted_rank_address as rr
import imperial_defect_autocomplexity_rank as ac
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

CUTS=(1,2,3,4,5)
FAMILIES=('prev4','prev8','prev4_left4','prevsign_leftsign','prev8_leftsign')
MAIN_FMT='<4sHHBBBBIII'
MAIN_SIZE=struct.calcsize(MAIN_FMT)

def clip(v,r):return max(-r,min(r,int(v)))+r
def sgn(v):return 0 if v==0 else (1 if v>0 else 2)

def low_ctx(prefix,bit,p,l,fam):
    if fam=='prev4':return (bit,prefix,clip(p,4))
    if fam=='prev8':return (bit,prefix,clip(p,8))
    if fam=='prev4_left4':return (bit,prefix,clip(p,4),clip(l,4))
    if fam=='prevsign_leftsign':return (bit,prefix,sgn(p),sgn(l))
    if fam=='prev8_leftsign':return (bit,prefix,clip(p,8),sgn(l))
    raise ValueError(fam)

def best_high_planes(u,nb,cut):
    known=np.zeros_like(u,np.uint64);out=bytearray();detail=[]
    for bit in range(nb-1,cut-1,-1):
        B=((u>>bit)&1).astype(np.uint8);best=None
        for fid in range(len(rr.FAMILIES)):
            payload,d=rr.encode_candidate(B,known,bit,fid);d={'mode':'static',**d}
            if best is None or len(payload)<len(best[0]):best=(payload,d)
        for cfid in range(len(ac.CAUSAL)):
            payload,d=ac.encode_causal_candidate(B,known,bit,cfid)
            if len(payload)<len(best[0]):best=(payload,d)
        payload,d=best;out.extend(payload);detail.append({'bit':bit,**d});known|=B.astype(np.uint64)<<bit
    return bytes(out),known,detail

def parse_high(buf,off,known,nb,cut):
    for bit in range(nb-1,cut-1,-1):
        fid,cm,am,clen,nbits,alen=struct.unpack_from('<BBBIII',buf,off);off+=15
        cstore=buf[off:off+clen];off+=clen;astore=buf[off:off+alen];off+=alen
        craw=m.D.decompress(cstore) if cm else cstore;araw=m.D.decompress(astore) if am else astore
        if fid<32:B=ac.decode_static_plane(fid,craw,araw,nbits,known,bit,known.shape)
        else:B=ac.decode_causal_plane(fid,craw,araw,nbits,known,bit,known.shape)
        known|=B.astype(np.uint64)<<bit
    return off,known

def encode_candidate(K,cut,fid):
    K=np.asarray(K,np.int32);u=m.zig(K);mx=int(u.max()) if u.size else 0;nb=max(1,mx.bit_length())
    if cut>=nb:raise RuntimeError(('cut too high',cut,nb))
    high,known,hdetail=best_high_planes(u,nb,cut);fam=FAMILIES[fid];counts={};enc=rr.ArithEncoder();C,T=K.shape
    for c in range(C):
        for t in range(T):
            p=int(K[c,t-1]) if t>0 else 0;l=int(K[c-1,t]) if c>0 else 0
            prefix=int(u[c,t]>>cut);z=int(u[c,t])
            for bit in range(cut-1,-1,-1):
                q=low_ctx(prefix,bit,p,l,fam);a=counts.get(q)
                if a is None:a=[1,1];counts[q]=a
                b=(z>>bit)&1;enc.encode(b,a[0],a[1]);a[b]+=1;prefix=(prefix<<1)|b
    lowraw,low_nbits=enc.finish();lz=m.Z.compress(lowraw)
    if len(lz)<len(lowraw):zf=1;lowstore=lz
    else:zf=0;lowstore=lowraw
    head=struct.pack(MAIN_FMT,b'HAS1',K.shape[0],K.shape[1],nb,cut,fid,zf,len(high),int(low_nbits),len(lowstore));buf=head+high+lowstore
    detail={'cut':cut,'family':fam,'nbits':nb,'high_bytes':len(high),'low_bytes':len(lowstore),'low_arith_bits':int(low_nbits),'low_contexts':len(counts),'low_zstd':bool(zf),'header_bytes':MAIN_SIZE,'high_planes':hdetail,'frame_bytes':len(buf)}
    return buf,detail

def decode_frame(buf):
    magic,C,T,nb,cut,fid,zf,hlen,low_nbits,llen=struct.unpack_from(MAIN_FMT,buf,0)
    if magic!=b'HAS1':raise RuntimeError('hybrid magic')
    off=MAIN_SIZE;high_end=off+hlen;known=np.zeros((C,T),np.uint64);off,known=parse_high(buf,off,known,nb,cut)
    if off!=high_end:raise RuntimeError(('high length',off,high_end))
    lowstore=buf[off:off+llen];off+=llen
    if off!=len(buf):raise RuntimeError(('hybrid trailing',off,len(buf)))
    lowraw=m.D.decompress(lowstore) if zf else lowstore;dec=rr.ArithDecoder(lowraw,low_nbits);fam=FAMILIES[fid];Kd=np.zeros((C,T),np.int32);counts={};uu=known.copy()
    for c in range(C):
        for t in range(T):
            p=int(Kd[c,t-1]) if t>0 else 0;l=int(Kd[c-1,t]) if c>0 else 0;prefix=int(uu[c,t]>>cut)
            for bit in range(cut-1,-1,-1):
                q=low_ctx(prefix,bit,p,l,fam);a=counts.get(q)
                if a is None:a=[1,1];counts[q]=a
                b=dec.decode(a[0],a[1]);a[b]+=1;prefix=(prefix<<1)|b;uu[c,t]|=np.uint64(b)<<np.uint64(bit)
            Kd[c,t]=int(m.unzig(np.asarray([uu[c,t]],np.uint64))[0])
    return Kd

def validate(X,eps,mb,cd,R,K,cut,fid):
    buf,detail=encode_candidate(K,cut,fid);Kd=decode_frame(buf)
    if not np.array_equal(Kd,K):raise RuntimeError(('hybrid K replay',cut,FAMILIES[fid]))
    Rd=np.zeros_like(R)
    for c in range(K.shape[0]):
        for t in range(K.shape[1]):Rd[c,t]=g.ar.predict_hist(Rd,c,t,cd,g.P,'shared')+base.STEP*int(Kd[c,t])
    if not np.array_equal(Rd,R):raise RuntimeError(('hybrid AR replay',cut,FAMILIES[fid]))
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('hybrid hard',me,eps))
    total=int(mb)+len(buf)+base.HEADER
    return {'cut':cut,'family':FAMILIES[fid],'bytes':int(total),'bps':8*total/X.size,'model_bytes':int(mb),'address_bytes':len(buf),'maxerr':me,'detail':detail}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);mb,cd,R,K=base.build_ar32(X);ab,arep,AK,ad=ac.autocomplexity_frame(K)
    if not np.array_equal(AK,K):raise RuntimeError('AUTO reference replay')
    auto={'bytes':int(mb+ab+base.HEADER),'address_bytes':int(ab),'bps':8*(mb+ab+base.HEADER)/X.size,'rep':arep}
    rows=[]
    for cut in CUTS:
        for fid in range(len(FAMILIES)):
            z=validate(X,eps,mb,cd,R,K,cut,fid);z['gain_vs_auto']=auto['bytes']/z['bytes'];z['gain_vs_sz3']=szb/z['bytes'];rows.append(z);print(json.dumps({k:v for k,v in z.items() if k!='detail'},indent=2),flush=True)
    rows.sort(key=lambda x:x['bytes']);best=rows[0]
    out={'region':'hard','shape':[g.C,g.T],'samples':int(X.size),'global_std':std,'eps':eps,'step':base.STEP,'cuts':list(CUTS),'families':list(FAMILIES),'sz3':{'bytes':int(szb),'bps':8*szb/X.size,'orientation':ori},'auto_incumbent':auto,'rows':rows,'best':best,'scope':'Exact hybrid address on the frozen AR32 step267 K field. Upper zigzag bitplanes are encoded exactly with the existing AUTO-COMPLEXITY per-plane competition (static constrained ranks versus causal same-plane type classes). At a public cut bit, decoding switches to symbol-major order for only the low bits. Because all upper planes are already known globally and each prior symbol is then completed before the next symbol, low-bit contexts can use the complete previous same-channel K and complete current-left K while retaining AUTO-COMPLEXITY high-plane savings. Low-bit probabilities are learned online with 1/1 counts; no target probability table is transmitted. Cut, family, framing and arithmetic payload are physical bytes. Decoder reproduces identical K, identical AR32 R and verifies unchanged hard source error.'}
    json.dump(out,open('imperial_ar32_hybrid_auto_symbol_address.json','w'),indent=2)
    print(json.dumps({'summary':{'best_cut':best['cut'],'best_family':best['family'],'best_bytes':best['bytes'],'auto_bytes':auto['bytes'],'sz3_bytes':int(szb),'gain_auto':auto['bytes']/best['bytes'],'gain_sz3':int(szb)/best['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
