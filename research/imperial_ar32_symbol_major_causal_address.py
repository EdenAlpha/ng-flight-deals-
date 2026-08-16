import json,sys,struct
import h5py,numpy as np
import imperial_ar32_autocomplexity_address as base
import imperial_defect_autocomplexity_rank as ac
import imperial_defect_restricted_rank_address as rr
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

FAMILIES=('prefix','prefix_prev4','prefix_prev8','prefix_prev4_left4','prefix_prev8_left4','prefix_prev4_left4_diag4','prefix_prevsign_leftsign')
HEADER=16

def clip(v,r):return max(-r,min(r,int(v)))+r

def sgn(v):return 0 if v==0 else (1 if v>0 else 2)

def ctx(prefix,bit,p,l,d,fam):
    # Prefix is the already-decoded higher bits of the current zigzag symbol.
    if fam=='prefix':return (bit,prefix)
    if fam=='prefix_prev4':return (bit,prefix,clip(p,4))
    if fam=='prefix_prev8':return (bit,prefix,clip(p,8))
    if fam=='prefix_prev4_left4':return (bit,prefix,clip(p,4),clip(l,4))
    if fam=='prefix_prev8_left4':return (bit,prefix,clip(p,8),clip(l,4))
    if fam=='prefix_prev4_left4_diag4':return (bit,prefix,clip(p,4),clip(l,4),clip(d,4))
    if fam=='prefix_prevsign_leftsign':return (bit,prefix,sgn(p),sgn(l))
    raise ValueError(fam)

def encode_family(K,fid):
    fam=FAMILIES[fid];K=np.asarray(K,np.int32);u=m.zig(K);mx=int(u.max()) if u.size else 0;nb=max(1,mx.bit_length());counts={};enc=rr.ArithEncoder()
    C,T=K.shape
    for c in range(C):
        for t in range(T):
            p=int(K[c,t-1]) if t>0 else 0;l=int(K[c-1,t]) if c>0 else 0;d=int(K[c-1,t-1]) if c>0 and t>0 else 0
            prefix=0;z=int(u[c,t])
            for bit in range(nb-1,-1,-1):
                q=ctx(prefix,bit,p,l,d,fam);a=counts.get(q)
                if a is None:a=[1,1];counts[q]=a
                b=(z>>bit)&1;enc.encode(b,a[0],a[1]);a[b]+=1;prefix=(prefix<<1)|b
    raw,nbits=enc.finish();z=m.Z.compress(raw)
    if len(z)<len(raw):zf=1;store=z
    else:zf=0;store=raw
    head=struct.pack('<4sBBBBII',b'SMC1',fid,nb,zf,0,int(nbits),len(store));buf=head+store
    return buf,{'family':fam,'nbits':nb,'contexts':len(counts),'arith_bits':int(nbits),'payload_bytes':len(store),'zstd':bool(zf),'frame_bytes':len(buf)}

def decode_frame(buf,shape):
    hs=struct.calcsize('<4sBBBBII');magic,fid,nb,zf,_,nbits,nstore=struct.unpack_from('<4sBBBBII',buf,0)
    if magic!=b'SMC1':raise RuntimeError('SMC magic')
    store=buf[hs:hs+nstore]
    if hs+nstore!=len(buf):raise RuntimeError('SMC trailing')
    raw=m.D.decompress(store) if zf else store;dec=rr.ArithDecoder(raw,nbits);fam=FAMILIES[fid];K=np.zeros(shape,np.int32);counts={}
    for c in range(shape[0]):
        for t in range(shape[1]):
            p=int(K[c,t-1]) if t>0 else 0;l=int(K[c-1,t]) if c>0 else 0;d=int(K[c-1,t-1]) if c>0 and t>0 else 0
            prefix=0
            for bit in range(nb-1,-1,-1):
                q=ctx(prefix,bit,p,l,d,fam);a=counts.get(q)
                if a is None:a=[1,1];counts[q]=a
                b=dec.decode(a[0],a[1]);a[b]+=1;prefix=(prefix<<1)|b
            K[c,t]=int(m.unzig(np.asarray([prefix],np.uint64))[0])
    return K

def validate(X,eps,mb,cd,R,K,fid):
    buf,detail=encode_family(K,fid);Kd=decode_frame(buf,K.shape)
    if not np.array_equal(Kd,K):raise RuntimeError(('SMC K replay',FAMILIES[fid]))
    Rd=np.zeros_like(R)
    for c in range(K.shape[0]):
        for t in range(K.shape[1]):Rd[c,t]=g.ar.predict_hist(Rd,c,t,cd,g.P,'shared')+base.STEP*int(Kd[c,t])
    if not np.array_equal(Rd,R):raise RuntimeError(('SMC AR replay',FAMILIES[fid]))
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('SMC hard',me,eps))
    total=int(mb)+len(buf)+base.HEADER
    return {'family':FAMILIES[fid],'bytes':int(total),'bps':8*total/X.size,'model_bytes':int(mb),'address_bytes':len(buf),'maxerr':me,'detail':detail}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);mb,cd,R,K=base.build_ar32(X);ab,arep,AK,ad=ac.autocomplexity_frame(K)
    if not np.array_equal(AK,K):raise RuntimeError('AUTO reference replay')
    auto={'bytes':int(mb+ab+base.HEADER),'address_bytes':int(ab),'bps':8*(mb+ab+base.HEADER)/X.size,'rep':arep}
    rows=[]
    for fid in range(len(FAMILIES)):
        z=validate(X,eps,mb,cd,R,K,fid);z['gain_vs_auto']=auto['bytes']/z['bytes'];z['gain_vs_sz3']=szb/z['bytes'];rows.append(z);print(json.dumps({k:v for k,v in z.items() if k!='detail'},indent=2),flush=True)
    rows.sort(key=lambda x:x['bytes']);best=rows[0]
    out={'region':'hard','shape':[g.C,g.T],'samples':int(X.size),'global_std':std,'eps':eps,'step':base.STEP,'families':list(FAMILIES),'sz3':{'bytes':int(szb),'bps':8*szb/X.size,'orientation':ori},'auto_incumbent':auto,'rows':rows,'best':best,'scope':'Exact symbol-major causal arithmetic address on the frozen AR32 step267 innovation field. Unlike the current plane-major AUTO-COMPLEXITY stream, each signed K symbol is decoded completely before the next symbol, so the probability context for the next symbol can use the full previous same-channel K, full current-left K and diagonal K at zero communication cost, plus the already-decoded higher-bit prefix of the current zigzag symbol. Binary probabilities are learned online from prior decoded bits with symmetric 1/1 counts; no target-trained tables or context histograms are transmitted. Public context-family selector, bit width, arithmetic framing and optional Zstd wrapper are in the real stream. Decoder reproduces identical K, recursively regenerates identical AR32 R and verifies the unchanged source hard error. This directly attacks bits 1-3 where the current plane-major codec lacks complete previous-symbol state.'}
    json.dump(out,open('imperial_ar32_symbol_major_causal_address.json','w'),indent=2)
    print(json.dumps({'summary':{'best_family':best['family'],'best_bytes':best['bytes'],'auto_bytes':auto['bytes'],'sz3_bytes':int(szb),'gain_auto':auto['bytes']/best['bytes'],'gain_sz3':int(szb)/best['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
