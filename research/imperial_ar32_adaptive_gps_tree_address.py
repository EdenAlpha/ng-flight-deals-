import json,sys,math,struct,functools
import h5py,numpy as np
import imperial_ar32_autocomplexity_address as base
import imperial_defect_restricted_rank_address as rr
import imperial_defect_autocomplexity_rank as ac
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

MAGIC=b'AGP1'
TREE_FID=64
MIN_C=2
MIN_T=32
MAX_DEPTH=7


def vlen(x):
    x=int(x);n=1
    while x>=128:n+=1;x>>=7
    return n


def logcomb(n,k):
    n=int(n);k=int(k)
    if k<=0 or k>=n:return 0.0
    return (math.lgamma(n+1)-math.lgamma(k+1)-math.lgamma(n-k+1))/math.log(2.0)


def rect_sum(P,c0,c1,t0,t1):
    return int(P[c1,t1]-P[c0,t1]-P[c1,t0]+P[c0,t0])


def build_tree(B):
    B=np.asarray(B,np.uint8);P=np.pad(B.astype(np.int32),((1,0),(1,0))).cumsum(0).cumsum(1)
    @functools.lru_cache(None)
    def dp(c0,c1,t0,t1,depth):
        n=(c1-c0)*(t1-t0);k=rect_sum(P,c0,c1,t0,t1)
        # one byte node marker + exact k varint + exact rank inside leaf
        best_cost=8.0*(1+vlen(k))+logcomb(n,k);best=('L',c0,c1,t0,t1,k)
        if depth<MAX_DEPTH:
            nc=c1-c0;nt=t1-t0
            if nt>=2*MIN_T:
                tm=(t0+t1)//2
                a,ca=dp(c0,c1,t0,tm,depth+1);b,cb=dp(c0,c1,tm,t1,depth+1)
                cost=8.0+ca+cb
                if cost+1e-9<best_cost:best_cost=cost;best=('T',a,b)
            if nc>=2*MIN_C:
                cm=(c0+c1)//2
                a,ca=dp(c0,cm,t0,t1,depth+1);b,cb=dp(cm,c1,t0,t1,depth+1)
                cost=8.0+ca+cb
                if cost+1e-9<best_cost:best_cost=cost;best=('C',a,b)
        return best,best_cost
    return dp(0,B.shape[0],0,B.shape[1],0)


def tree_stats(node):
    if node[0]=='L':return 1,1,0
    a=tree_stats(node[1]);b=tree_stats(node[2]);return a[0]+b[0]+1,a[1]+b[1],a[2]+b[2]+1


def serialize_tree(node,out,leaves):
    typ=node[0]
    if typ=='L':
        out.append(0);rr.put_uvar(out,int(node[5]));leaves.append(node);return
    out.append(1 if typ=='T' else 2);serialize_tree(node[1],out,leaves);serialize_tree(node[2],out,leaves)


def parse_tree(buf,pos,c0,c1,t0,t1):
    if pos>=len(buf):raise RuntimeError('tree eof')
    tag=buf[pos];pos+=1
    if tag==0:
        k,pos=rr.get_uvar(buf,pos);n=(c1-c0)*(t1-t0)
        if k>n:raise RuntimeError(('tree count',k,n))
        return ('L',c0,c1,t0,t1,int(k)),pos
    if tag==1:
        if t1-t0<2:raise RuntimeError('bad time split')
        tm=(t0+t1)//2;a,pos=parse_tree(buf,pos,c0,c1,t0,tm);b,pos=parse_tree(buf,pos,c0,c1,tm,t1);return ('T',a,b),pos
    if tag==2:
        if c1-c0<2:raise RuntimeError('bad channel split')
        cm=(c0+c1)//2;a,pos=parse_tree(buf,pos,c0,cm,t0,t1);b,pos=parse_tree(buf,pos,cm,c1,t0,t1);return ('C',a,b),pos
    raise RuntimeError(('tree tag',tag))


def collect_leaves(node,out):
    if node[0]=='L':out.append(node);return
    collect_leaves(node[1],out);collect_leaves(node[2],out)


def iter_rect(B,node):
    _,c0,c1,t0,t1,_=node
    for t in range(t0,t1):
        for c in range(c0,c1):yield int(B[c,t])


def tree_candidate(B):
    node,proxy=build_tree(B);meta=bytearray();leaves=[];serialize_tree(node,meta,leaves);meta=bytes(meta)
    ae=rr.ArithEncoder()
    for leaf in leaves:
        n=(leaf[2]-leaf[1])*(leaf[4]-leaf[3]);rk=int(leaf[5]);rn=n
        for b in iter_rect(B,leaf):
            if rk!=0 and rk!=rn:ae.encode(b,rn-rk,rk)
            rn-=1;rk-=b
        if rk!=0:raise RuntimeError(('tree encode remainder',rk))
    araw,nbits=ae.finish();mz=m.Z.compress(meta);az=m.Z.compress(araw)
    if len(mz)<len(meta):cm=1;cstore=mz
    else:cm=0;cstore=meta
    if len(az)<len(araw):am=1;astore=az
    else:am=0;astore=araw
    head=struct.pack('<BBBIII',TREE_FID,cm,am,len(cstore),int(nbits),len(astore));nodes,nleaf,nsplit=tree_stats(node)
    payload=head+cstore+astore
    return payload,{'mode':'adaptive_gps_tree','nodes':nodes,'leaves':nleaf,'splits':nsplit,'meta_bytes':len(cstore),'arith_bytes':len(astore),'arith_bits':int(nbits),'proxy_bits':float(proxy),'stored':len(payload)}


def decode_tree_plane(craw,araw,nbits,shape):
    node,pos=parse_tree(craw,0,0,shape[0],0,shape[1])
    if pos!=len(craw):raise RuntimeError(('tree meta trailing',pos,len(craw)))
    leaves=[];collect_leaves(node,leaves);B=np.zeros(shape,np.uint8);ad=rr.ArithDecoder(araw,nbits)
    for leaf in leaves:
        _,c0,c1,t0,t1,k=leaf;rn=(c1-c0)*(t1-t0);rk=int(k)
        for t in range(t0,t1):
            for c in range(c0,c1):
                if rk==0:b=0
                elif rk==rn:b=1
                else:b=ad.decode(rn-rk,rk)
                B[c,t]=b;rn-=1;rk-=b
        if rk!=0:raise RuntimeError(('tree decode remainder',rk))
    return B


def adaptive_gps_frame(A):
    A=np.asarray(A,np.int32);u=m.zig(A);mx=int(u.max()) if u.size else 0;nb=max(1,mx.bit_length());known=np.zeros_like(u,np.uint64)
    out=bytearray(struct.pack('<4sHHB',MAGIC,A.shape[0],A.shape[1],nb));detail=[]
    for bit in range(nb-1,-1,-1):
        B=((u>>bit)&1).astype(np.uint8);best=None
        for fid in range(len(rr.FAMILIES)):
            payload,d=rr.encode_candidate(B,known,bit,fid);d={'mode':'static',**d}
            if best is None or len(payload)<len(best[0]):best=(payload,d)
        for cfid in range(len(ac.CAUSAL)):
            payload,d=ac.encode_causal_candidate(B,known,bit,cfid)
            if len(payload)<len(best[0]):best=(payload,d)
        payload,d=tree_candidate(B)
        if len(payload)<len(best[0]):best=(payload,d)
        payload,d=best;out.extend(payload);detail.append({'bit':bit,**d});known|=B.astype(np.uint64)<<bit
    buf=bytes(out);off=0;magic,nc,nt,nb2=struct.unpack_from('<4sHHB',buf,off);off+=9
    if magic!=MAGIC or (nc,nt)!=(A.shape[0],A.shape[1]) or nb2!=nb:raise RuntimeError('adaptive GPS header')
    uu=np.zeros_like(u,np.uint64)
    for bit in range(nb-1,-1,-1):
        fid,cm,am,clen,nbits,alen=struct.unpack_from('<BBBIII',buf,off);off+=15;cstore=buf[off:off+clen];off+=clen;astore=buf[off:off+alen];off+=alen
        craw=m.D.decompress(cstore) if cm else cstore;araw=m.D.decompress(astore) if am else astore
        if fid<TREE_FID:
            if fid<32:B=ac.decode_static_plane(fid,craw,araw,nbits,uu,bit,A.shape)
            else:B=ac.decode_causal_plane(fid,craw,araw,nbits,uu,bit,A.shape)
        elif fid==TREE_FID:B=decode_tree_plane(craw,araw,nbits,A.shape)
        else:raise RuntimeError(('unknown adaptive fid',fid))
        uu|=B.astype(np.uint64)<<bit
    if off!=len(buf):raise RuntimeError(('adaptive GPS trailing',off,len(buf)))
    Ad=m.unzig(uu).astype(np.int32)
    if not np.array_equal(Ad,A):raise RuntimeError('adaptive GPS K replay')
    return len(buf),'adaptive_gps_tree_rank',Ad,detail


def validate(X,eps,mb,cd,R,K,frame_fn,kind):
    fb,rep,Kd,detail=frame_fn(K);Kd=np.asarray(Kd,np.int32)
    if not np.array_equal(Kd,K):raise RuntimeError((kind,'K mismatch'))
    Rd=np.zeros_like(R)
    for c in range(K.shape[0]):
        for t in range(K.shape[1]):Rd[c,t]=g.ar.predict_hist(Rd,c,t,cd,g.P,'shared')+base.STEP*int(Kd[c,t])
    if not np.array_equal(Rd,R):raise RuntimeError((kind,'AR replay'))
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError((kind,'hard',me,eps))
    total=int(mb)+int(fb)+base.HEADER
    return {'kind':kind,'bytes':int(total),'bps':8*total/X.size,'model_bytes':int(mb),'address_bytes':int(fb),'maxerr':me,'rep':rep,'detail':detail}


def auto_frame(K):
    b,rep,Kd,d=ac.autocomplexity_frame(K);return int(b),rep,Kd,d


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);mb,cd,R,K=base.build_ar32(X);rows=[]
    rows.append(validate(X,eps,mb,cd,R,K,auto_frame,'autocomplexity'))
    rows.append(validate(X,eps,mb,cd,R,K,adaptive_gps_frame,'adaptive_gps'))
    for z in rows:z['gain_vs_sz3']=szb/z['bytes'];print(json.dumps({k:v for k,v in z.items() if k!='detail'},indent=2),flush=True)
    rows.sort(key=lambda x:x['bytes']);best=rows[0];ag=next(x for x in rows if x['kind']=='adaptive_gps');auto=next(x for x in rows if x['kind']=='autocomplexity')
    out={'region':'hard','shape':[g.C,g.T],'samples':int(X.size),'global_std':std,'eps':eps,'step':base.STEP,'sz3':{'bytes':int(szb),'bps':8*szb/X.size,'orientation':ori},'rows':rows,'best':best,'adaptive_detail':ag['detail'],'scope':'Exact ADAPTIVE GPS / hierarchical constrained-address gate on the frozen incumbent AR32 K field. Each zigzag bitplane competes between the existing exact static type-class ranks, exact causal AUTO-COMPLEXITY ranks, and a transmitted adaptive binary partition tree over channel-time coordinates. A tree node is split in time or channel only when a dynamic-programming codelength objective says the two child restricted universes plus the charged split metadata are cheaper than ranking the parent universe. Every leaf stores its exact one-count and arithmetic-ranks the leaf pattern without replacement among C(n,k) candidates. The full tree topology and all leaf counts are serialized (and optionally Zstd-compressed); no partition is free. Decoder parses the transmitted tree, reconstructs every exact bitplane and identical K, then recursively reproduces identical AR32 R and verifies source hard error. This is a concrete version of NOVA Fast Adaptive GPS: recursively ask location questions only when they shorten the real address.'}
    json.dump(out,open('imperial_ar32_adaptive_gps_tree_address.json','w'),indent=2)
    print(json.dumps({'summary':{'adaptive_bytes':ag['bytes'],'auto_bytes':auto['bytes'],'best_kind':best['kind'],'best_bytes':best['bytes'],'sz3_bytes':int(szb),'gain_auto':auto['bytes']/ag['bytes'],'gain_sz3':int(szb)/ag['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
