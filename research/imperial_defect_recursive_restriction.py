import json,sys,struct,math
import h5py,numpy as np
import imperial_defect_restricted_rank_address as rr
import imperial_defect_contour_address as c
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

MIN_AREA=128
MIN_T=8
MIN_C=2
SPLIT_GAIN_BITS=6.0


def uvar_len(x):
    x=int(x);n=1
    while x>=128:n+=1;x>>=7
    return n


def logcomb(n,k):
    if k<0 or k>n:return 1e30
    if k==0 or k==n:return 0.0
    return (math.lgamma(n+1)-math.lgamma(k+1)-math.lgamma(n-k+1))/math.log(2.0)


def region_groups(B,known,bit,box):
    c0,c1,t0,t1=box
    P=(known[c0:c1,t0:t1]>>(bit+1)).astype(np.uint64).ravel()
    X=np.asarray(B[c0:c1,t0:t1],np.uint8).ravel()
    order=np.argsort(P,kind='stable');Ps=P[order];Xs=X[order]
    if Ps.size==0:return []
    cuts=np.flatnonzero(Ps[1:]!=Ps[:-1])+1
    starts=np.r_[0,cuts];ends=np.r_[cuts,Ps.size]
    out=[]
    for a,z in zip(starts,ends):
        idx=order[int(a):int(z)];n=int(z-a);k=int(Xs[int(a):int(z)].sum())
        out.append((idx,n,k))
    return out


def leaf_cost(B,known,bit,box):
    s=2.0
    for _,n,k in region_groups(B,known,bit,box):
        s += 8*uvar_len(k)+logcomb(n,k)
    return s


def build_tree(B,known,bit,box):
    c0,c1,t0,t1=box;nc=c1-c0;nt=t1-t0;area=nc*nt
    lc=leaf_cost(B,known,bit,box)
    best=(lc,('L',box))
    if area>=2*MIN_AREA and nt>=2*MIN_T:
        tm=(t0+t1)//2
        a=build_tree(B,known,bit,(c0,c1,t0,tm));b=build_tree(B,known,bit,(c0,c1,tm,t1));sc=2.0+a[0]+b[0]
        if sc+SPLIT_GAIN_BITS<best[0]:best=(sc,('T',box,a[1],b[1]))
    if area>=2*MIN_AREA and nc>=2*MIN_C:
        cm=(c0+c1)//2
        a=build_tree(B,known,bit,(c0,cm,t0,t1));b=build_tree(B,known,bit,(cm,c1,t0,t1));sc=2.0+a[0]+b[0]
        if sc+SPLIT_GAIN_BITS<best[0]:best=(sc,('C',box,a[1],b[1]))
    return best


def tree_commands(node,cmds,leaves):
    typ=node[0]
    if typ=='L':cmds.append(0);leaves.append(node[1]);return
    if typ=='T':cmds.append(1)
    elif typ=='C':cmds.append(2)
    else:raise ValueError(typ)
    tree_commands(node[2],cmds,leaves);tree_commands(node[3],cmds,leaves)


def pack_cmds(cmds):
    out=bytearray((len(cmds)+3)//4)
    for i,x in enumerate(cmds):out[i>>2]|=(int(x)&3)<<((i&3)*2)
    return bytes(out)


def unpack_cmds(raw,n):
    return [int((raw[i>>2]>>((i&3)*2))&3) for i in range(n)]


def rebuild_tree(cmds,pos,box):
    if pos[0]>=len(cmds):raise RuntimeError('tree eof')
    typ=cmds[pos[0]];pos[0]+=1;c0,c1,t0,t1=box
    if typ==0:return ('L',box)
    if typ==1:
        tm=(t0+t1)//2
        a=rebuild_tree(cmds,pos,(c0,c1,t0,tm));b=rebuild_tree(cmds,pos,(c0,c1,tm,t1));return ('T',box,a,b)
    if typ==2:
        cm=(c0+c1)//2
        a=rebuild_tree(cmds,pos,(c0,cm,t0,t1));b=rebuild_tree(cmds,pos,(cm,c1,t0,t1));return ('C',box,a,b)
    raise RuntimeError(('bad tree cmd',typ))


def encode_plane(B,known,bit):
    _,tree=build_tree(B,known,bit,(0,B.shape[0],0,B.shape[1]));cmds=[];leaves=[];tree_commands(tree,cmds,leaves)
    counts=bytearray();ae=rr.ArithEncoder();ng=0
    for box in leaves:
        c0,c1,t0,t1=box;sub=np.asarray(B[c0:c1,t0:t1],np.uint8).ravel()
        for idx,n,k in region_groups(B,known,bit,box):
            rr.put_uvar(counts,k);ng+=1;rn=n;rk=k
            for local in idx:
                b=int(sub[int(local)])
                if rk!=0 and rk!=rn:ae.encode(b,rn-rk,rk)
                rn-=1;rk-=b
    araw,nbits=ae.finish();az=m.Z.compress(araw);am=1 if len(az)<len(araw) else 0;astore=az if am else araw
    traw=pack_cmds(cmds);tz=m.Z.compress(traw);tm=1 if len(tz)<len(traw) else 0;tstore=tz if tm else traw
    craw=bytes(counts);cz=m.Z.compress(craw);cm=1 if len(cz)<len(craw) else 0;cstore=cz if cm else craw
    head=struct.pack('<4sHBBIII',b'RRP1',len(cmds),tm,cm,len(tstore),len(cstore),int(nbits))+struct.pack('<BI',am,len(astore))
    return head+tstore+cstore+astore,{'nodes':len(cmds),'leaves':len(leaves),'groups':ng,'tree_bytes':len(tstore),'count_bytes':len(cstore),'arith_bytes':len(astore),'arith_bits':int(nbits)}


def decode_plane(payload,known,bit,shape):
    off=0;magic,ncmd,tm,cm,tlen,clen,nbits=struct.unpack_from('<4sHBBIII',payload,off);off+=20;am,alen=struct.unpack_from('<BI',payload,off);off+=5
    if magic!=b'RRP1':raise RuntimeError('plane magic')
    tstore=payload[off:off+tlen];off+=tlen;cstore=payload[off:off+clen];off+=clen;astore=payload[off:off+alen];off+=alen
    if off!=len(payload):raise RuntimeError('plane trailing')
    traw=m.D.decompress(tstore) if tm else tstore;craw=m.D.decompress(cstore) if cm else cstore;araw=m.D.decompress(astore) if am else astore
    cmds=unpack_cmds(traw,ncmd);pos=[0];tree=rebuild_tree(cmds,pos,(0,shape[0],0,shape[1]))
    if pos[0]!=len(cmds):raise RuntimeError('unused tree')
    leaves=[];dummy=[];tree_commands(tree,dummy,leaves);ad=rr.ArithDecoder(araw,nbits);B=np.zeros(shape,np.uint8);cp=0
    for box in leaves:
        c0,c1,t0,t1=box;sub=np.zeros((c1-c0,t1-t0),np.uint8);dummyB=np.zeros(shape,np.uint8)
        # groups depend only on decoded higher planes, not this plane's unknown bits.
        for idx,n,_ in region_groups(dummyB,known,bit,box):
            k,cp=rr.get_uvar(craw,cp)
            if k>n:raise RuntimeError(('count',k,n));rn=n;rk=int(k);flat=sub.ravel()
            for local in idx:
                if rk==0:b=0
                elif rk==rn:b=1
                else:b=ad.decode(rn-rk,rk)
                flat[int(local)]=b;rn-=1;rk-=b
            if rk:raise RuntimeError('rank remainder')
        B[c0:c1,t0:t1]=sub
    if cp!=len(craw):raise RuntimeError(('count trailing',cp,len(craw)))
    return B


def recursive_frame(A):
    A=np.asarray(A,np.int32);u=m.zig(A);mx=int(u.max()) if u.size else 0;nb=max(1,mx.bit_length());known=np.zeros_like(u,np.uint64)
    out=bytearray(struct.pack('<4sHHB',b'RRR1',A.shape[0],A.shape[1],nb));detail=[]
    for bit in range(nb-1,-1,-1):
        B=((u>>bit)&1).astype(np.uint8);payload,d=encode_plane(B,known,bit);out.extend(struct.pack('<I',len(payload)));out.extend(payload);detail.append({'bit':bit,**d});known|=B.astype(np.uint64)<<bit
    buf=bytes(out);off=9;magic,nc,nt,nb2=struct.unpack_from('<4sHHB',buf,0)
    if magic!=b'RRR1' or (nc,nt)!=A.shape or nb2!=nb:raise RuntimeError('frame head')
    uu=np.zeros_like(u,np.uint64)
    for bit in range(nb-1,-1,-1):
        L=struct.unpack_from('<I',buf,off)[0];off+=4;payload=buf[off:off+L];off+=L;B=decode_plane(payload,uu,bit,A.shape);uu|=B.astype(np.uint64)<<bit
    if off!=len(buf):raise RuntimeError('frame trailing')
    Ad=m.unzig(uu).astype(np.int32)
    if not np.array_equal(Ad,A):raise RuntimeError('recursive replay')
    return len(buf),'recursive_restriction',Ad,detail


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);arb=g.ar32_baseline(X,eps);h,Q,E,dts,dcs,co,intercept,score,nz,changes=c.build_resonant(X,eps)
    rb,rrname,RE,rdetail=rr.restricted_rank_frame(E);base=c.validate(X,eps,h,Q,RE,dts,dcs,co,intercept,rb,rrname,rdetail)
    xb,xname,XE,xdetail=recursive_frame(E);rec=c.validate(X,eps,h,Q,XE,dts,dcs,co,intercept,xb,xname,xdetail)
    rows=[base,rec]
    for r in rows:r['gain_vs_sz3']=szb/r['bytes'];r['gain_vs_ar32']=arb['bytes']/r['bytes'];print(json.dumps({k:v for k,v in r.items() if k!='detail'},indent=2),flush=True)
    rows.sort(key=lambda x:x['bytes']);best=rows[0]
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'sz3':{'bytes':int(szb),'orientation':ori},'ar32':arb,'rows':rows,'best':best,'recursive_detail':xdetail,'scope':'Exact recursive restriction codec. It keeps the PR512 learned-law reconstruction unchanged and changes only the signed defect address. Each zigzag bitplane is decoded MSB-first. Within each plane, a charged binary partition tree recursively chooses leaf vs time/channel split only when an estimated enumerative address saves enough bits after topology/count cost. Inside each leaf, already-decoded higher-bit prefixes restrict positions into deterministic groups; exact one-counts are stored and the observed pattern is arithmetic-ranked among C(n,k) candidates. Tree topology, counts, rank stream, selectors and framing are real bytes and independently decoded. The identical defect raster, Q field and source-domain hard-error reconstruction are replayed. No ideal restriction gain is counted.'}
    json.dump(out,open('imperial_defect_recursive_restriction.json','w'),indent=2)
    print(json.dumps({'summary':{'best':best['rep'],'bytes':best['bytes'],'recursive_total':rec['bytes'],'rank_total':base['bytes'],'ar32':arb['bytes'],'sz3':int(szb)}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
