import itertools,json,os,struct,sys
import numpy as np
import zstandard as zstd

# Reuse audited geometry and PR #126 event-gap/outlier helpers.
src=open('research/soda_event_gap.py').read().split('\npath=sys.argv[1]')[0]
exec(compile(src,'soda_event_gap.py','exec'),globals())

CMAG=b'TC4Gv001'; CH='<8sBBBB4II'; CHS=struct.calcsize(CH)


def class_id(v):
    if v==1:return 0
    if v==-1:return 1
    if v>1:return 2
    if v<-1:return 3
    return -1


def build(K,order):
    P=np.transpose(K,order+(3,));sh=P.shape;tr=P.reshape(-1,sh[-1]);counts=np.zeros((4,tr.shape[0]),np.uint16);gby=[[] for _ in range(4)];mags=[]
    for i,row in enumerate(tr):
        for ci in range(4):
            if ci==0:pos=np.flatnonzero(row==1)
            elif ci==1:pos=np.flatnonzero(row==-1)
            elif ci==2:pos=np.flatnonzero(row>1)
            else:pos=np.flatnonzero(row<-1)
            counts[ci,i]=pos.size
            if not pos.size:continue
            g=np.empty(pos.size,np.int32);g[0]=pos[0]+1
            if pos.size>1:g[1:]=np.diff(pos)
            gby[ci].extend(g.tolist())
            if ci>=2:mags.extend((np.abs(row[pos]).astype(np.int32)-2).tolist())
    return counts,[np.asarray(x,np.int32) for x in gby],np.asarray(mags,np.int32),sh


def enc(K,order,level,split):
    zc=zstd.ZstdCompressor(level=level);counts,gby,mags,psh=build(K,order);frames=[]
    if split:
        for ci in range(4):
            frames.append(zc.compress(counts[ci].astype('<u2',copy=False).tobytes()));frames.append(zc.compress(leb128_u(gby[ci])))
        tn=8
    else:
        gg=np.concatenate(gby) if sum(x.size for x in gby) else np.empty(0,np.int32);frames=[zc.compress(counts.astype('<u2',copy=False).tobytes()),zc.compress(leb128_u(gg))];tn=2
    dc=dtype_code(mags);mb=zc.compress(mags.astype(DT[dc],copy=False).tobytes()) if mags.size else zc.compress(b'');frames.append(mb);nf=len(frames);oc=int(order[0]|(order[1]<<2)|(order[2]<<4));h=struct.pack(CH,CMAG,1,oc,int(split),dc,*K.shape,nf);lb=b''.join(struct.pack('<Q',len(x)) for x in frames)
    ce=[int(counts[i].sum()) for i in range(4)]
    parts={'order':list(order),'level':level,'timing_mode':'split4' if split else 'combined','class_events':{'+1':ce[0],'-1':ce[1],'>1':ce[2],'<-1':ce[3]},'events':sum(ce),'exception_events':ce[2]+ce[3],'counts_bytes':sum(len(frames[i]) for i in range(0,tn,2)) if split else len(frames[0]),'gaps_bytes':sum(len(frames[i]) for i in range(1,tn,2)) if split else len(frames[1]),'timing_bytes':sum(len(x) for x in frames[:tn]),'magnitude_bytes':len(mb),'frame_lengths_bytes':len(lb),'raw_varint_bytes':sum(len(leb128_u(x)) for x in gby)}
    return h+lb+b''.join(frames),parts


def dec(blob):
    magic,ver,oc,split,dc,C,L,S,T,nf=struct.unpack(CH,blob[:CHS])
    if magic!=CMAG or ver!=1:raise RuntimeError('class header')
    order=tuple((oc>>(2*i))&3 for i in range(3));psh=tuple((C,L,S)[i] for i in order)+(T,);ntr=int(np.prod(psh[:-1]));p=CHS;lens=[]
    for _ in range(nf):lens.append(struct.unpack('<Q',blob[p:p+8])[0]);p+=8
    fs=[]
    for n in lens:fs.append(blob[p:p+n]);p+=n
    if p!=len(blob):raise RuntimeError('class stream length')
    zd=zstd.ZstdDecompressor()
    if not split:
        if nf!=3:raise RuntimeError(('combined nf',nf));counts=np.frombuffer(zd.decompress(fs[0]),'<u2',count=4*ntr).astype(np.int32).reshape(4,ntr);ne=int(counts.sum());gaps=leb128_decode(zd.decompress(fs[1]),ne);mn=2
    else:
        if nf!=9:raise RuntimeError(('split nf',nf));counts=np.empty((4,ntr),np.int32);gg=[]
        for ci in range(4):
            counts[ci]=np.frombuffer(zd.decompress(fs[2*ci]),'<u2',count=ntr).astype(np.int32);n=int(counts[ci].sum());gg.extend(leb128_decode(zd.decompress(fs[2*ci+1]),n).tolist())
        gaps=np.asarray(gg,np.int32);mn=8
    nex=int(counts[2].sum()+counts[3].sum());mags=np.frombuffer(zd.decompress(fs[mn]),dtype=DT[dc],count=nex).astype(np.int32) if nex else np.empty(0,np.int32)
    tr=np.zeros((ntr,T),np.int32);kg=0;km=0
    for ci in range(4):
        for i in range(ntr):
            c=int(counts[ci,i])
            if not c:continue
            g=gaps[kg:kg+c];kg+=c;pos=np.cumsum(g)-1
            if pos[-1]>=T:raise RuntimeError('class event position')
            if ci==0:tr[i,pos]=1
            elif ci==1:tr[i,pos]=-1
            elif ci==2:
                tr[i,pos]=mags[km:km+c]+2;km+=c
            else:
                tr[i,pos]=-(mags[km:km+c]+2);km+=c
    if kg!=gaps.size or km!=mags.size:raise RuntimeError(('class accounting',kg,gaps.size,km,mags.size))
    P=tr.reshape(psh);inv=np.argsort(order);return np.transpose(P,tuple(inv)+(3,))


def best_out(O):
    rows=[]
    for td in (False,True):
        A=delta(O,1) if td else O;K4=A.reshape(1,1,A.shape[0],A.shape[1])
        for vm in (0,1):
            for level in (19,22):
                b,parts=encode(K4,(0,1,2),vm,level);R=decode(b).reshape(O.shape);RR=undelta(R,1) if td else R
                if not np.array_equal(RR,O):raise RuntimeError('out gap')
                rows.append((len(b),'gap',td,vm,level,None,b,parts))
        for level in (19,22):
            for perm in ((0,1,2,3),(3,1,2,0)):
                for rep in (0,1,2):
                    b=encode_out_sparse(A,perm,rep,level);R=decode_out_sparse(b);RR=undelta(R,1) if td else R
                    if not np.array_equal(RR,O):raise RuntimeError('out generic')
                    rows.append((len(b),'generic',td,rep,level,perm,b,{}))
    return min(rows,key=lambda x:x[0])


def main(path):
    X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());eps=.1*std;step=2*eps;raw=X.nbytes;G,tm,outids,geom=geometry_map(X,gx,gy)
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    O=np.rint(X[outids]/step).astype(np.int32);K=delta(G,3);rows=[]
    for order in itertools.permutations((0,1,2)):
        for level in (19,22):
            for split in (False,True):
                b,parts=enc(K,order,level,split);R=dec(b)
                if not np.array_equal(R,K):raise RuntimeError(('transition-class decode',order,level,split))
                rows.append((len(b),order,level,split,b,parts))
    rows.sort(key=lambda x:x[0]);bm=rows[0];bo=best_out(O);topfmt='<8sdQQB';top=struct.pack(topfmt,b'TC4TOP01',eps,len(bm[4]),len(bo[6]),0 if bo[1]=='gap' else 1)+bm[4]+bo[6];hs=struct.calcsize(topfmt);_,ee,lm,lo,ok=struct.unpack(topfmt,top[:hs]);RK=dec(top[hs:hs+lm]);obb=top[hs+lm:hs+lm+lo]
    if ok==0:
        A=decode(obb).reshape(O.shape);RO=undelta(A,1) if bo[2] else A
    else:
        A=decode_out_sparse(obb);RO=undelta(A,1) if bo[2] else A
    RG=undelta(RK,3);Y=np.empty_like(X)
    for tid,c,l,s in tm:Y[tid]=RG[c,l,s].astype(np.float32)*np.float32(2*ee)
    Y[outids]=RO.astype(np.float32)*np.float32(2*ee);me=float(np.max(np.abs(X-Y)));szb,sze=sz3_bytes(X,eps)
    cands=[{'bytes':r[0],'order':list(r[1]),'level':r[2],'timing_mode':'split4' if r[3] else 'combined','parts':r[5]} for r in rows]
    outmeta={'bytes':bo[0],'kind':bo[1],'tdiff':bo[2],'mode':bo[3],'level':bo[4],'perm':list(bo[5]) if bo[5] is not None else None,'parts':bo[7]}
    out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'eps':eps,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'main_best':cands[0],'main_candidates':cands,'outlier_best':outmeta,'container_bytes':len(top),'ratio':raw/len(top),'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'sz3':{'bytes':szb,'ratio':raw/szb,'maxerr':sze},'gain_vs_direct_sz3':szb/len(top),'strongest_verified_p75_baseline_bytes':133225,'gain_vs_strongest_verified_p75_baseline':133225/len(top),'two_x_gate_bytes':133225/2,'prior_event_gap_frontier_bytes':70208}
    print(json.dumps(out,indent=2),flush=True);json.dump(out,open('soda_transition_class_gap.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
