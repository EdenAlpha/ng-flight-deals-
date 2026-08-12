import itertools,json,os,struct,sys
import numpy as np
import zstandard as zstd

# Reuse audited Soda geometry, integer lattice, value coding, and outlier helpers.
src=open('research/soda_event_gap.py').read().split('\npath=sys.argv[1]')[0]
exec(compile(src,'soda_event_gap.py','exec'),globals())

MAG=b'NEEDv001'; H='<8sBBBB4II'; HS=struct.calcsize(H)


def greedy_match(prev,cur,W):
    m=cur.size;n=prev.size;match=np.full(m,-1,np.int32);i=j=0
    while i<m and j<n:
        a=int(cur[i]);b=int(prev[j])
        if b<a-W:
            j+=1
        elif a<b-W:
            i+=1
        else:
            # Both lie in the admissible window. Prefer the nearer of j and j+1
            # only when doing so cannot skip a current event.
            jj=j
            if j+1<n and abs(int(prev[j+1])-a)<abs(b-a) and int(prev[j+1])<=a+W:
                jj=j+1
            match[i]=jj;i+=1;j=jj+1
    return match


def spatial_rows(K,order):
    P=np.transpose(K,order+(3,));sh=P.shape;return P.reshape(-1,sh[-1]),sh


def build_script(K,order,W,thr):
    tr,sh=spatial_rows(K,order);ntr,T=tr.shape;fast=sh[-2]
    counts=np.zeros(ntr,np.uint16);modes=np.zeros(ntr,np.uint8);rawg=[];flags=[];skips=[];resids=[];insg=[];matched=inserted=raw_events=0
    prev_pos=None
    for i,row in enumerate(tr):
        cur=np.flatnonzero(row!=0).astype(np.int32);c=cur.size;counts[i]=c
        reset=(i%fast)==0
        use=False;mapping=None
        if (not reset) and c and prev_pos is not None and prev_pos.size:
            mapping=greedy_match(prev_pos,cur,W);nm=int(np.count_nonzero(mapping>=0));use=nm>=max(2,int(np.ceil(thr*c)))
        if use:
            modes[i]=1;lastj=0;lastcur=-1
            for k,p in enumerate(cur.tolist()):
                j=int(mapping[k])
                if j>=0:
                    flags.append(1);skips.append(j-lastj);resids.append(p-int(prev_pos[j]));lastj=j+1;matched+=1
                else:
                    flags.append(0);insg.append(p-lastcur);inserted+=1
                lastcur=p
        else:
            if c:
                g=np.empty(c,np.int32);g[0]=cur[0]+1
                if c>1:g[1:]=np.diff(cur)
                rawg.extend(g.tolist());raw_events+=c
        prev_pos=cur
    return counts,modes,np.asarray(rawg,np.int32),np.asarray(flags,np.uint8),np.asarray(skips,np.int32),np.asarray(resids,np.int8),np.asarray(insg,np.int32),{'raw_events':raw_events,'matched_events':matched,'inserted_events':inserted,'neighbor_traces':int(modes.sum()),'raw_traces':int(ntr-modes.sum()),'total_events':int(counts.sum()),'match_fraction':matched/max(1,int(counts.sum()))}


def encode_candidate(K,order,W,thr,level):
    zc=zstd.ZstdCompressor(level=level);counts,modes,rawg,flags,skips,resids,insg,stats=build_script(K,order,W,thr);tr,sh=spatial_rows(K,order);M=tr!=0;vals=tr[M].astype(np.int32)
    sign=vals<0;ab=np.abs(vals);exc=ab!=1;mag=(ab[exc]-2).astype(np.int32);dc=dtype_code(mag)
    frames=[
        zc.compress(counts.astype('<u2',copy=False).tobytes()),
        zc.compress(np.packbits(modes,bitorder='little').tobytes()),
        zc.compress(leb128_u(rawg)),
        zc.compress(np.packbits(flags,bitorder='little').tobytes()),
        zc.compress(leb128_u(skips)),
        zc.compress(resids.tobytes()),
        zc.compress(leb128_u(insg)),
        zc.compress(np.packbits(sign,bitorder='little').tobytes()),
        zc.compress(np.packbits(exc,bitorder='little').tobytes()),
        zc.compress(mag.astype(DT[dc],copy=False).tobytes()) if mag.size else zc.compress(b'')]
    oc=int(order[0]|(order[1]<<2)|(order[2]<<4));h=struct.pack(H,MAG,1,oc,dc,0,*K.shape,len(frames));lb=b''.join(struct.pack('<Q',len(x)) for x in frames)
    parts={**stats,'order':list(order),'W':W,'threshold':thr,'level':level,'counts':len(frames[0]),'modes':len(frames[1]),'raw_gaps':len(frames[2]),'flags':len(frames[3]),'skips':len(frames[4]),'residuals':len(frames[5]),'insert_gaps':len(frames[6]),'sign':len(frames[7]),'exception_support':len(frames[8]),'exception_magnitude':len(frames[9]),'timing_bytes':sum(len(x) for x in frames[:7]),'value_bytes':sum(len(x) for x in frames[7:]),'raw_gap_varint_bytes':len(leb128_u(rawg)),'skip_varint_bytes':len(leb128_u(skips)),'insert_varint_bytes':len(leb128_u(insg))}
    return h+lb+b''.join(frames),parts


def decode_candidate(blob):
    magic,ver,oc,dc,reserved,C,L,S,T,nf=struct.unpack(H,blob[:HS])
    if magic!=MAG or ver!=1 or nf!=10:raise RuntimeError('neighbor-edit header')
    order=tuple((oc>>(2*i))&3 for i in range(3));psh=tuple((C,L,S)[i] for i in order)+(T,);ntr=int(np.prod(psh[:-1]));fast=psh[-2];p=HS;lens=[]
    for _ in range(nf):
        lens.append(struct.unpack('<Q',blob[p:p+8])[0]);p+=8
    fs=[]
    for n in lens:
        fs.append(blob[p:p+n]);p+=n
    if p!=len(blob):raise RuntimeError('neighbor-edit length')
    zd=zstd.ZstdDecompressor();counts=np.frombuffer(zd.decompress(fs[0]),'<u2',count=ntr).astype(np.int32);modes=np.unpackbits(np.frombuffer(zd.decompress(fs[1]),np.uint8),bitorder='little',count=ntr).astype(bool)
    nraw=int(counts[~modes].sum());nneigh=int(counts[modes].sum());rawg=leb128_decode(zd.decompress(fs[2]),nraw);flags=np.unpackbits(np.frombuffer(zd.decompress(fs[3]),np.uint8),bitorder='little',count=nneigh).astype(bool);nmatch=int(flags.sum());nins=nneigh-nmatch;skips=leb128_decode(zd.decompress(fs[4]),nmatch);resids=np.frombuffer(zd.decompress(fs[5]),np.int8,count=nmatch).astype(np.int32);insg=leb128_decode(zd.decompress(fs[6]),nins)
    posrows=[];kr=ki=kf=ks=0;prev=None
    for i,c0 in enumerate(counts.tolist()):
        c=int(c0)
        if not modes[i]:
            if c:
                g=rawg[kr:kr+c];kr+=c;cur=np.cumsum(g)-1
            else:cur=np.empty(0,np.int32)
        else:
            if (i%fast)==0 or prev is None:raise RuntimeError('illegal neighbour mode at reset')
            cur=np.empty(c,np.int32);lastj=0;lastcur=-1
            for k in range(c):
                if flags[kf]:
                    j=lastj+int(skips[ks]);r=int(resids[ks]);ks+=1
                    if j<0 or j>=prev.size:raise RuntimeError('predictor index')
                    p0=int(prev[j])+r;lastj=j+1
                else:
                    p0=lastcur+int(insg[ki]);ki+=1
                if p0<=lastcur or p0<0 or p0>=T:raise RuntimeError(('decoded event order',i,k,p0,lastcur))
                cur[k]=p0;lastcur=p0;kf+=1
        posrows.append(cur);prev=cur
    if kr!=rawg.size or ki!=insg.size or ks!=skips.size or kf!=flags.size:raise RuntimeError(('timing accounting',kr,rawg.size,ki,insg.size,ks,skips.size,kf,flags.size))
    ne=int(counts.sum());sign=np.unpackbits(np.frombuffer(zd.decompress(fs[7]),np.uint8),bitorder='little',count=ne).astype(bool);exc=np.unpackbits(np.frombuffer(zd.decompress(fs[8]),np.uint8),bitorder='little',count=ne).astype(bool);ab=np.ones(ne,np.int32)
    if exc.any():ab[exc]=np.frombuffer(zd.decompress(fs[9]),dtype=DT[dc],count=int(exc.sum())).astype(np.int32)+2
    vals=np.where(sign,-ab,ab);tr=np.zeros((ntr,T),np.int32);q=0
    for i,pos in enumerate(posrows):
        c=pos.size
        if c:tr[i,pos]=vals[q:q+c];q+=c
    if q!=ne:raise RuntimeError('value accounting')
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
        for W in (2,4,8,16):
            for thr in (.25,.5,.75):
                for level in (19,22):
                    b,parts=encode_candidate(K,order,W,thr,level);R=decode_candidate(b)
                    if not np.array_equal(R,K):raise RuntimeError(('neighbor-edit K decode',order,W,thr,level))
                    rows.append((len(b),order,W,thr,level,b,parts))
    rows.sort(key=lambda x:x[0]);bm=rows[0];bo=best_out(O);topfmt='<8sdQQB';top=struct.pack(topfmt,b'NETOP001',eps,len(bm[5]),len(bo[6]),0 if bo[1]=='gap' else 1)+bm[5]+bo[6];hs=struct.calcsize(topfmt);_,ee,lm,lo,ok=struct.unpack(topfmt,top[:hs]);RK=decode_candidate(top[hs:hs+lm]);obb=top[hs+lm:hs+lm+lo]
    if ok==0:
        A=decode(obb).reshape(O.shape);RO=undelta(A,1) if bo[2] else A
    else:
        A=decode_out_sparse(obb);RO=undelta(A,1) if bo[2] else A
    RG=undelta(RK,3);Y=np.empty_like(X)
    for tid,c,l,s in tm:Y[tid]=RG[c,l,s].astype(np.float32)*np.float32(2*ee)
    Y[outids]=RO.astype(np.float32)*np.float32(2*ee);me=float(np.max(np.abs(X-Y)));szb,sze=sz3_bytes(X,eps)
    cands=[{'bytes':r[0],'order':list(r[1]),'W':r[2],'threshold':r[3],'level':r[4],'parts':r[6]} for r in rows[:20]];outmeta={'bytes':bo[0],'kind':bo[1],'tdiff':bo[2],'mode':bo[3],'level':bo[4],'perm':list(bo[5]) if bo[5] is not None else None,'parts':bo[7]}
    out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'eps':eps,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'main_best':cands[0],'main_candidates':cands,'outlier_best':outmeta,'container_bytes':len(top),'ratio':raw/len(top),'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'sz3':{'bytes':szb,'ratio':raw/szb,'maxerr':sze},'gain_vs_direct_sz3':szb/len(top),'strongest_verified_p75_baseline_bytes':133225,'gain_vs_strongest_verified_p75_baseline':133225/len(top),'two_x_gate_bytes':133225/2,'prior_event_gap_frontier_bytes':70208}
    print(json.dumps(out,indent=2),flush=True);json.dump(out,open('soda_neighbor_event_edit.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
