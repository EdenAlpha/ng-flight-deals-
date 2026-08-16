import json,sys,struct
import h5py,numpy as np
import imperial_address_aware_pair_search as p
import imperial_address_aware_legal_search as a
import imperial_defect_restricted_rank_address as rr
import imperial_defect_contour_address as c
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

MODES=('nbr3','mag4_nbr','prefix2_nbr','mag8_lu','c4_nbr','t4_nbr','mag4_c2_nbr')
ORDERS=('time_major','channel_major')


def ctx_id(known,cur,c0,t0,bit,mode):
    pref=int(known[c0,t0]>>(bit+1))
    l=int(cur[c0-1,t0]) if c0>0 else 0
    u=int(cur[c0,t0-1]) if t0>0 else 0
    d=int(cur[c0-1,t0-1]) if c0>0 and t0>0 else 0
    nbr=(l<<2)|(u<<1)|d
    if mode=='nbr3':return nbr,8
    if mode=='mag4_nbr':return min(pref,3)*8+nbr,32
    if mode=='prefix2_nbr':return (pref&3)*8+nbr,32
    if mode=='mag8_lu':return min(pref,7)*4+(l<<1)+u,32
    if mode=='c4_nbr':return (c0*4//known.shape[0])*8+nbr,32
    if mode=='t4_nbr':return (t0*4//known.shape[1])*8+nbr,32
    if mode=='mag4_c2_nbr':return (min(pref,3)*2+(c0*2//known.shape[0]))*8+nbr,64
    raise ValueError(mode)


def iter_coords(shape,order):
    nc,nt=shape
    if order=='time_major':
        for t in range(nt):
            for c0 in range(nc):yield c0,t
    else:
        for c0 in range(nc):
            for t in range(nt):yield c0,t


def encode_adaptive_plane(B,known,bit,mode,order):
    B=np.asarray(B,np.uint8);cur=np.zeros_like(B,np.uint8)
    _,nctx=ctx_id(known,cur,0,0,bit,mode);z=np.ones(nctx,np.int64);o=np.ones(nctx,np.int64);ae=rr.ArithEncoder()
    for c0,t0 in iter_coords(B.shape,order):
        k,_=ctx_id(known,cur,c0,t0,bit,mode);b=int(B[c0,t0]);ae.encode(b,int(z[k]),int(o[k]));cur[c0,t0]=b
        if b:o[k]+=1
        else:z[k]+=1
    raw,nbits=ae.finish();zz=m.Z.compress(raw)
    if len(zz)<len(raw):cm=1;store=zz
    else:cm=0;store=raw
    head=struct.pack('<BBII',MODES.index(mode),ORDERS.index(order),int(nbits),len(store))+bytes([cm])
    return head+store,{'mode':mode,'order':order,'arith_bits':int(nbits),'stored':len(head)+len(store),'payload_bytes':len(store),'zstd':bool(cm)}


def decode_adaptive_plane(payload,known,bit,shape):
    if len(payload)<11:raise RuntimeError('causal payload short')
    mi,oi,nbits,L=struct.unpack_from('<BBII',payload,0);cm=payload[10]
    if mi>=len(MODES) or oi>=len(ORDERS):raise RuntimeError('causal selector')
    store=payload[11:11+L]
    if 11+L!=len(payload):raise RuntimeError('causal trailing')
    raw=m.D.decompress(store) if cm else store
    mode=MODES[mi];order=ORDERS[oi];cur=np.zeros(shape,np.uint8)
    _,nctx=ctx_id(known,cur,0,0,bit,mode);z=np.ones(nctx,np.int64);o=np.ones(nctx,np.int64);ad=rr.ArithDecoder(raw,nbits)
    for c0,t0 in iter_coords(shape,order):
        k,_=ctx_id(known,cur,c0,t0,bit,mode);b=ad.decode(int(z[k]),int(o[k]));cur[c0,t0]=b
        if b:o[k]+=1
        else:z[k]+=1
    return cur


def causal_frame(A):
    A=np.asarray(A,np.int32);u=m.zig(A);mx=int(u.max()) if u.size else 0;nb=max(1,mx.bit_length());known=np.zeros_like(u,np.uint64)
    out=bytearray(struct.pack('<4sHHB',b'CAR1',A.shape[0],A.shape[1],nb));detail=[]
    for bit in range(nb-1,-1,-1):
        B=((u>>bit)&1).astype(np.uint8);best=None
        for mode in MODES:
            for order in ORDERS:
                payload,d=encode_adaptive_plane(B,known,bit,mode,order)
                if best is None or len(payload)<len(best[0]):best=(payload,d)
        payload,d=best;out.extend(struct.pack('<I',len(payload)));out.extend(payload);detail.append({'bit':bit,**d,'ones':int(B.sum())});known|=B.astype(np.uint64)<<bit
    buf=bytes(out);magic,nc,nt,nb2=struct.unpack_from('<4sHHB',buf,0);off=9
    if magic!=b'CAR1' or (nc,nt)!=A.shape or nb2!=nb:raise RuntimeError('causal header')
    uu=np.zeros_like(u,np.uint64)
    for bit in range(nb-1,-1,-1):
        L=struct.unpack_from('<I',buf,off)[0];off+=4;payload=buf[off:off+L];off+=L;B=decode_adaptive_plane(payload,uu,bit,A.shape);uu|=B.astype(np.uint64)<<bit
    if off!=len(buf):raise RuntimeError('causal frame trailing')
    Ad=m.unzig(uu).astype(np.int32)
    if not np.array_equal(Ad,A):raise RuntimeError('causal address replay')
    return len(buf),'causal_restricted_address',Ad,detail


def build_pair_state(X,eps):
    h,Q,D,dts,dcs,co,intercept,score,nz,base_changes=c.build_resonant(X,eps);lo,hi=g.legal_q(X,eps,h);logc=a.logcomb_table(X.size)
    Q=np.ascontiguousarray(Q.copy());D=np.ascontiguousarray(D.copy());Q,D,_,single_changes=a.shape_search(Q,lo,hi,D,dts,dcs,co,intercept,g.SCALE,logc,p.NBITS,a.PASSES)
    Q,D,_,pair_changes,tested,rejected=p.pair_search(np.ascontiguousarray(Q.copy()),lo,hi,np.ascontiguousarray(D.copy()),dts,dcs,co,intercept,g.SCALE,logc,p.NBITS,p.PAIR_PASSES)
    Dr=g._all_defects(Q,dts,dcs,co,intercept,g.SCALE)
    if not np.array_equal(Dr,D):raise RuntimeError('pair state mismatch')
    return h,Q,D,dts,dcs,co,intercept,{'base_changes':base_changes,'single_changes':single_changes,'pair_changes':pair_changes,'tested':tested,'rejected':rejected}


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);arb=g.ar32_baseline(X,eps);h,Q,D,dts,dcs,co,intercept,search=build_pair_state(X,eps)
    rb,_,RE,rdetail=rr.restricted_rank_frame(D);rank=c.validate(X,eps,h,Q,RE,dts,dcs,co,intercept,rb,'pair_restricted_rank',rdetail)
    cb,_,CE,cdetail=causal_frame(D);causal=c.validate(X,eps,h,Q,CE,dts,dcs,co,intercept,cb,'causal_restricted_address',cdetail)
    rows=[rank,causal]
    for r in rows:
        r['gain_vs_sz3']=szb/r['bytes'];r['gain_vs_ar32']=arb['bytes']/r['bytes'];print(json.dumps({k:v for k,v in r.items() if k!='detail'},indent=2),flush=True)
    rows.sort(key=lambda x:x['bytes']);best=rows[0]
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'h':h,'sz3':{'bytes':int(szb),'orientation':ori},'ar32':arb,'search':search,'rows':rows,'best':best,'causal_detail':cdetail,'scope':'Exact decoder-shared causal restriction address after PR530. The same hard-error-legal learned-law reconstruction and coordinated pair search are reproduced. Only the final defect address changes. Each signed zigzag bitplane is decoded MSB-first. Within a plane, a deterministic causal context is formed from already-decoded same-plane spatial/temporal/diagonal neighbors plus decoder-known higher-plane magnitude/coordinate classes. Context probabilities start from public unit pseudocounts and adapt identically at encoder and decoder, so no target-trained probability table is transmitted. Per plane the encoder searches a small public menu of context grammars and two causal scan orders; selector, arithmetic bit count, payload, optional Zstd wrapping and framing are all real bytes. The byte-decoded planes must reproduce the identical defect raster, exact Q field and unchanged source-domain hard error. PR512 restricted ranking on the identical pair-optimized state is rerun as fallback. No oracle entropy is counted.'}
    json.dump(out,open('imperial_causal_restricted_address.json','w'),indent=2)
    print(json.dumps({'summary':{'best':best['rep'],'bytes':best['bytes'],'rank':rank['bytes'],'causal':causal['bytes'],'ar32':arb['bytes'],'sz3':int(szb),'gain_ar32':best['gain_vs_ar32']}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
