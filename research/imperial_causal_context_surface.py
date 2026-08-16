import json,sys,struct
import h5py,numpy as np
import imperial_causal_restricted_address as base
import imperial_defect_restricted_rank_address as rr
import imperial_defect_contour_address as c
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

MODES=(
'nbr3','nbr5','nbr5_mag2','nbr5_mag4','nbr_sum_mag4','temporal3_l','spatial3_u',
'highnbr_nbr3','highcross_nbr3','prefix2_nbr5','mag8_nbr5','c2_mag4_nbr5','t2_mag4_nbr5',
'run_t','run_c','run_tc'
)
ORDERS=('time_major','channel_major')


def bit_at(A,c0,t0):
    if c0<0 or t0<0 or c0>=A.shape[0] or t0>=A.shape[1]:return 0
    return int(A[c0,t0])


def ctx_id(known,cur,c0,t0,bit,mode):
    pref=int(known[c0,t0]>>(bit+1));mag2=min(pref,1);mag4=min(pref,3);mag8=min(pref,7)
    l=bit_at(cur,c0-1,t0);u=bit_at(cur,c0,t0-1);d=bit_at(cur,c0-1,t0-1)
    l2=bit_at(cur,c0-2,t0);u2=bit_at(cur,c0,t0-2);l3=bit_at(cur,c0-3,t0);u3=bit_at(cur,c0,t0-3)
    n3=(l<<2)|(u<<1)|d;n5=(l<<4)|(u<<3)|(d<<2)|(l2<<1)|u2
    hp=(known>>(bit+1))&1
    hl=bit_at(hp,c0-1,t0);hu=bit_at(hp,c0,t0-1);hd=bit_at(hp,c0-1,t0-1)
    if mode=='nbr3':return n3,8
    if mode=='nbr5':return n5,32
    if mode=='nbr5_mag2':return mag2*32+n5,64
    if mode=='nbr5_mag4':return mag4*32+n5,128
    if mode=='nbr_sum_mag4':return mag4*16+(l+u+d)*4+(l2<<1)+u2,64
    if mode=='temporal3_l':return (((u<<1)|u2)<<1|u3)*2+l,16
    if mode=='spatial3_u':return (((l<<1)|l2)<<1|l3)*2+u,16
    if mode=='highnbr_nbr3':return ((hl<<2)|(hu<<1)|hd)*8+n3,64
    if mode=='highcross_nbr3':return ((hl<<1)|hu)*8+n3,32
    if mode=='prefix2_nbr5':return (pref&3)*32+n5,128
    if mode=='mag8_nbr5':return mag8*32+n5,256
    if mode=='c2_mag4_nbr5':return (mag4*2+(c0*2//known.shape[0]))*32+n5,256
    if mode=='t2_mag4_nbr5':return (mag4*2+(t0*2//known.shape[1]))*32+n5,256
    if mode=='run_t':return ((u<<1)|u2)*4+(min(pref,3)),16
    if mode=='run_c':return ((l<<1)|l2)*4+(min(pref,3)),16
    if mode=='run_tc':return ((u<<2)|(u2<<1)|l)*4+min(pref,3),32
    raise ValueError(mode)


def iter_coords(shape,order):
    nc,nt=shape
    if order=='time_major':
        for t in range(nt):
            for c0 in range(nc):yield c0,t
    else:
        for c0 in range(nc):
            for t in range(nt):yield c0,t


def encode_plane(B,known,bit,mode,order):
    B=np.asarray(B,np.uint8);cur=np.zeros_like(B,np.uint8);_,nctx=ctx_id(known,cur,0,0,bit,mode)
    z=np.ones(nctx,np.int64);o=np.ones(nctx,np.int64);ae=rr.ArithEncoder()
    for c0,t0 in iter_coords(B.shape,order):
        k,_=ctx_id(known,cur,c0,t0,bit,mode);b=int(B[c0,t0]);ae.encode(b,int(z[k]),int(o[k]));cur[c0,t0]=b
        if b:o[k]+=1
        else:z[k]+=1
    raw,nbits=ae.finish();zz=m.Z.compress(raw);cm=1 if len(zz)<len(raw) else 0;store=zz if cm else raw
    head=struct.pack('<BBII',MODES.index(mode),ORDERS.index(order),int(nbits),len(store))+bytes([cm])
    return head+store,{'mode':mode,'order':order,'arith_bits':int(nbits),'stored':len(head)+len(store),'payload_bytes':len(store),'zstd':bool(cm)}


def decode_plane(payload,known,bit,shape):
    mi,oi,nbits,L=struct.unpack_from('<BBII',payload,0);cm=payload[10]
    if mi>=len(MODES) or oi>=len(ORDERS) or 11+L!=len(payload):raise RuntimeError('selector/frame')
    raw=m.D.decompress(payload[11:]) if cm else payload[11:];mode=MODES[mi];order=ORDERS[oi]
    cur=np.zeros(shape,np.uint8);_,nctx=ctx_id(known,cur,0,0,bit,mode);z=np.ones(nctx,np.int64);o=np.ones(nctx,np.int64);ad=rr.ArithDecoder(raw,nbits)
    for c0,t0 in iter_coords(shape,order):
        k,_=ctx_id(known,cur,c0,t0,bit,mode);b=ad.decode(int(z[k]),int(o[k]));cur[c0,t0]=b
        if b:o[k]+=1
        else:z[k]+=1
    return cur


def frame(A):
    A=np.asarray(A,np.int32);u=m.zig(A);mx=int(u.max()) if u.size else 0;nb=max(1,mx.bit_length());known=np.zeros_like(u,np.uint64)
    out=bytearray(struct.pack('<4sHHB',b'CAS2',A.shape[0],A.shape[1],nb));detail=[]
    for bit in range(nb-1,-1,-1):
        B=((u>>bit)&1).astype(np.uint8);best=None
        for mode in MODES:
            for order in ORDERS:
                p,d=encode_plane(B,known,bit,mode,order)
                if best is None or len(p)<len(best[0]):best=(p,d)
        p,d=best;out.extend(struct.pack('<I',len(p)));out.extend(p);detail.append({'bit':bit,**d,'ones':int(B.sum())});known|=B.astype(np.uint64)<<bit
    buf=bytes(out);magic,nc,nt,nb2=struct.unpack_from('<4sHHB',buf,0);off=9
    if magic!=b'CAS2' or (nc,nt)!=A.shape or nb2!=nb:raise RuntimeError('head')
    uu=np.zeros_like(u,np.uint64)
    for bit in range(nb-1,-1,-1):
        L=struct.unpack_from('<I',buf,off)[0];off+=4;p=buf[off:off+L];off+=L;B=decode_plane(p,uu,bit,A.shape);uu|=B.astype(np.uint64)<<bit
    if off!=len(buf):raise RuntimeError('trailing')
    Ad=m.unzig(uu).astype(np.int32)
    if not np.array_equal(Ad,A):raise RuntimeError('surface replay')
    return len(buf),'causal_context_surface',Ad,detail


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);arb=g.ar32_baseline(X,eps);h,Q,D,dts,dcs,co,intercept,search=base.build_pair_state(X,eps)
    bb,bname,BE,bdetail=base.causal_frame(D);old=c.validate(X,eps,h,Q,BE,dts,dcs,co,intercept,bb,'old_causal',bdetail)
    nb,nname,NE,ndetail=frame(D);new=c.validate(X,eps,h,Q,NE,dts,dcs,co,intercept,nb,nname,ndetail)
    for r in (old,new):r['gain_vs_sz3']=szb/r['bytes'];r['gain_vs_ar32']=arb['bytes']/r['bytes'];print(json.dumps({k:v for k,v in r.items() if k!='detail'},indent=2),flush=True)
    best=min((old,new),key=lambda r:r['bytes']);out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'sz3':{'bytes':int(szb),'orientation':ori},'ar32':arb,'search':search,'old':old,'new':new,'best':best,'new_detail':ndetail,'scope':'Exact zero-side-information causal context surface on the identical PR530 pair-optimized hard-Imperial reconstruction. It expands only the public per-bitplane context grammar: 5-neighbor same-plane contexts, short temporal/spatial runs, higher-plane neighbor bits, magnitude buckets and coarse coordinate mixtures. All probabilities are decoder-shared online adaptive counts initialized to public unit pseudocounts. Per-plane grammar/order selector, arithmetic payload and framing are real bytes. No learned probability table is transmitted. The exact signed defect, Q field and hard-error source reconstruction must replay. PR537 is rerun on the identical state as floor.'};json.dump(out,open('imperial_causal_context_surface.json','w'),indent=2)
    print(json.dumps({'summary':{'old':old['bytes'],'new':new['bytes'],'best':best['bytes'],'ar32':arb['bytes'],'sz3':int(szb),'gap_to_ar32':best['bytes']-arb['bytes']}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
