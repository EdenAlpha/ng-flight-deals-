import json,sys,struct
import h5py,numpy as np
import imperial_defect_contour_address as c
import imperial_defect_restricted_rank_address as r
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

CAUSAL=(
 ('lu',4),
 ('lud',8),
 ('luu2',8),
 ('lud_hi1',16),
 ('lud_hi2',32),
 ('lud_c4',32),
 ('lud_t4',32),
 ('lud_tphase4',32),
 ('lud_cphase4',32),
 ('lud_hi1_c2',32),
)


def ctx_id(B,known,bit,family,c0,t0):
    l=int(B[c0-1,t0]) if c0>0 else 0
    u=int(B[c0,t0-1]) if t0>0 else 0
    d=int(B[c0-1,t0-1]) if c0>0 and t0>0 else 0
    u2=int(B[c0,t0-2]) if t0>1 else 0
    if family=='lu':return l|(u<<1)
    if family=='lud':return l|(u<<1)|(d<<2)
    if family=='luu2':return l|(u<<1)|(u2<<2)
    base=l|(u<<1)|(d<<2)
    hi1=(int(known[c0,t0])>>(bit+1))&1
    hi2=(int(known[c0,t0])>>(bit+1))&3
    if family=='lud_hi1':return base|(hi1<<3)
    if family=='lud_hi2':return base|(hi2<<3)
    if family=='lud_c4':return base|((c0*4//B.shape[0])<<3)
    if family=='lud_t4':return base|((t0*4//B.shape[1])<<3)
    if family=='lud_tphase4':return base|((t0&3)<<3)
    if family=='lud_cphase4':return base|((c0&3)<<3)
    if family=='lud_hi1_c2':return base|(hi1<<3)|((c0*2//B.shape[0])<<4)
    raise ValueError(family)


def encode_causal_candidate(B,known,bit,cfid):
    family,nctx=CAUSAL[cfid];B=np.asarray(B,np.uint8);ns=np.zeros(nctx,np.int64);ks=np.zeros(nctx,np.int64)
    for t in range(B.shape[1]):
        for cc in range(B.shape[0]):
            q=ctx_id(B,known,bit,family,cc,t);ns[q]+=1;ks[q]+=int(B[cc,t])
    counts=bytearray()
    for n,k in zip(ns,ks):r.put_uvar(counts,int(n));r.put_uvar(counts,int(k))
    craw=bytes(counts);cz=m.Z.compress(craw)
    if len(cz)<len(craw):cm=1;cstore=cz
    else:cm=0;cstore=craw
    rn=ns.copy();rk=ks.copy();ae=r.ArithEncoder()
    for t in range(B.shape[1]):
        for cc in range(B.shape[0]):
            q=ctx_id(B,known,bit,family,cc,t);b=int(B[cc,t]);n=int(rn[q]);k=int(rk[q])
            if k!=0 and k!=n:ae.encode(b,n-k,k)
            rn[q]-=1;rk[q]-=b
    if np.any(rn) or np.any(rk):raise RuntimeError(('causal encode remainder',family,rn.tolist(),rk.tolist()))
    araw,nbits=ae.finish();az=m.Z.compress(araw)
    if len(az)<len(araw):am=1;astore=az
    else:am=0;astore=araw
    fid=32+cfid;head=struct.pack('<BBBIII',fid,cm,am,len(cstore),int(nbits),len(astore));payload=head+cstore+astore
    return payload,{'mode':'causal','family':family,'contexts':nctx,'count_bytes':len(cstore),'arith_bytes':len(astore),'arith_bits':int(nbits),'ones':int(B.sum()),'stored':len(payload)}


def decode_static_plane(fid,craw,araw,nbits,known,bit,shape):
    keys=r.context_keys(known,bit,r.FAMILIES[fid]);order,starts,ends=r.groups_for(keys);ks=[];p=0
    for a,z in zip(starts,ends):
        k,p=r.get_uvar(craw,p);n=int(z-a)
        if k>n:raise RuntimeError(('static count range',bit,k,n))
        ks.append(int(k))
    if p!=len(craw):raise RuntimeError(('static count trailing',bit,p,len(craw)))
    ad=r.ArithDecoder(araw,nbits);sorted_bits=np.empty(shape[0]*shape[1],np.uint8)
    for a,z,k in zip(starts,ends,ks):
        rn=int(z-a);rk=int(k)
        for j in range(int(a),int(z)):
            if rk==0:b=0
            elif rk==rn:b=1
            else:b=ad.decode(rn-rk,rk)
            sorted_bits[j]=b;rn-=1;rk-=b
        if rk!=0:raise RuntimeError(('static remainder',bit,rk))
    flat=np.empty(shape[0]*shape[1],np.uint8);flat[order]=sorted_bits
    return flat.reshape(shape)


def decode_causal_plane(fid,craw,araw,nbits,known,bit,shape):
    cfid=fid-32;family,nctx=CAUSAL[cfid];ns=np.zeros(nctx,np.int64);ks=np.zeros(nctx,np.int64);p=0
    for i in range(nctx):
        n,p=r.get_uvar(craw,p);k,p=r.get_uvar(craw,p)
        if k>n:raise RuntimeError(('causal count range',family,i,n,k))
        ns[i]=n;ks[i]=k
    if p!=len(craw):raise RuntimeError(('causal count trailing',family,p,len(craw)))
    B=np.zeros(shape,np.uint8);rn=ns.copy();rk=ks.copy();ad=r.ArithDecoder(araw,nbits)
    for t in range(shape[1]):
        for cc in range(shape[0]):
            q=ctx_id(B,known,bit,family,cc,t);n=int(rn[q]);k=int(rk[q])
            if n<=0:raise RuntimeError(('causal occurrence underflow',family,q,cc,t))
            if k==0:b=0
            elif k==n:b=1
            else:b=ad.decode(n-k,k)
            B[cc,t]=b;rn[q]-=1;rk[q]-=b
    if np.any(rn) or np.any(rk):raise RuntimeError(('causal decode remainder',family,rn.tolist(),rk.tolist()))
    return B


def autocomplexity_frame(A):
    A=np.asarray(A,np.int32);u=m.zig(A);mx=int(u.max()) if u.size else 0;nb=max(1,mx.bit_length());known=np.zeros_like(u,np.uint64)
    out=bytearray(struct.pack('<4sHHB',b'ACR1',A.shape[0],A.shape[1],nb));detail=[]
    for bit in range(nb-1,-1,-1):
        B=((u>>bit)&1).astype(np.uint8);best=None
        for fid in range(len(r.FAMILIES)):
            payload,d=r.encode_candidate(B,known,bit,fid);d={'mode':'static',**d}
            if best is None or len(payload)<len(best[0]):best=(payload,d)
        for cfid in range(len(CAUSAL)):
            payload,d=encode_causal_candidate(B,known,bit,cfid)
            if len(payload)<len(best[0]):best=(payload,d)
        payload,d=best;out.extend(payload);detail.append({'bit':bit,**d});known|=B.astype(np.uint64)<<bit
    buf=bytes(out);off=0;magic,nc,nt,nb2=struct.unpack_from('<4sHHB',buf,off);off+=9
    if magic!=b'ACR1' or (nc,nt)!=(A.shape[0],A.shape[1]) or nb2!=nb:raise RuntimeError('auto rank header')
    uu=np.zeros_like(u,np.uint64)
    for bit in range(nb-1,-1,-1):
        fid,cm,am,clen,nbits,alen=struct.unpack_from('<BBBIII',buf,off);off+=15;cstore=buf[off:off+clen];off+=clen;astore=buf[off:off+alen];off+=alen
        craw=m.D.decompress(cstore) if cm else cstore;araw=m.D.decompress(astore) if am else astore
        if fid<32:B=decode_static_plane(fid,craw,araw,nbits,uu,bit,A.shape)
        else:B=decode_causal_plane(fid,craw,araw,nbits,uu,bit,A.shape)
        uu|=B.astype(np.uint64)<<bit
    if off!=len(buf):raise RuntimeError(('auto rank trailing',off,len(buf)))
    Ad=m.unzig(uu).astype(np.int32)
    if not np.array_equal(Ad,A):raise RuntimeError('autocomplexity replay')
    return len(buf),'autocomplexity_rank',Ad,detail


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);arb=g.ar32_baseline(X,eps);h,Q,E,dts,dcs,co,intercept,score,nz,changes=c.build_resonant(X,eps)
    rows=[]
    rb,rr,RE,rdetail=r.restricted_rank_frame(E);rows.append(c.validate(X,eps,h,Q,RE,dts,dcs,co,intercept,rb,rr,rdetail))
    cb,cr,CE,cdetail=c.bitplane_contour_frame(E);rows.append(c.validate(X,eps,h,Q,CE,dts,dcs,co,intercept,cb,cr,cdetail))
    ab,ar,AE,adetail=autocomplexity_frame(E);rows.append(c.validate(X,eps,h,Q,AE,dts,dcs,co,intercept,ab,ar,adetail))
    for x in rows:
        x['gain_vs_sz3']=szb/x['bytes'];x['gain_vs_ar32']=arb['bytes']/x['bytes'];print(json.dumps({k:v for k,v in x.items() if k!='detail'},indent=2),flush=True)
    rows.sort(key=lambda x:x['bytes']);best=rows[0]
    out={'region':'hard','shape':[g.C,g.T],'samples':int(X.size),'global_std':std,'eps':eps,'h':h,'sz3':{'bytes':int(szb),'bps':8*szb/X.size,'orientation':ori},'ar32':arb,'rows':rows,'best':best,'autocomplexity_detail':adetail,'scope':'Exact AUTO-COMPLEXITY constrained-address gate derived from the uploaded complexity_weapon.py. The charged learned generator and globally legal reconstruction are unchanged. Bitplanes decode MSB to LSB. In addition to the exact static context-rank families from PR512, this stream searches causal type classes whose state is determined by already-decoded bits in the same plane: left/up, left/up/diagonal, second temporal predecessor, higher decoded magnitude bits, fixed channel/time partitions, and fixed coordinate phases. For a causal state the encoder transmits both its exact occurrence count and one-count, then arithmetic-ranks each next bit without replacement inside that state. Occurrence counts are necessary because causal state occupancy itself depends on the sequence, and they are fully charged. The decoder reproduces the same causal state online from prior decoded bits, consumes the transmitted type-class counts, recovers the exact plane and verifies every count is exhausted. Per-plane choice between static and causal restriction is stored in the real stream. Final signed defect, Q reconstruction and source-domain hard error replay exactly. This is a concrete invertible version of prefix-learns-structure / file-constrains-itself; no approximate restriction factors, ideal entropy or uncharged model is counted.'}
    json.dump(out,open('imperial_defect_autocomplexity_rank.json','w'),indent=2)
    arow=next(x for x in rows if x['rep']=='autocomplexity_rank')
    print(json.dumps({'summary':{'auto_total':arow['bytes'],'restricted_total':next(x['bytes'] for x in rows if x['rep']=='restricted_rank'),'contour_total':next(x['bytes'] for x in rows if x['rep']=='bitplane_contour'),'ar32_bytes':arb['bytes'],'sz3_bytes':int(szb),'auto_vs_ar32':arb['bytes']/arow['bytes'],'auto_vs_sz3':int(szb)/arow['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
