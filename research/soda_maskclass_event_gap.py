import json,os,struct,sys
import numpy as np
import zstandard as zstd

# Reuse audited Soda geometry and PR #126 event-gap / outlier helpers.
src=open('research/soda_event_gap.py').read().split('\npath=sys.argv[1]')[0]
exec(compile(src,'soda_event_gap.py','exec'),globals())

MAG7=b'MC7Gv002'; H7='<8sBBBBB4II'; H7S=struct.calcsize(H7)


def site_order(L,S,code):
    if code==0:return [(l,s) for l in range(L) for s in range(S)]
    if code==1:return [(l,s) for s in range(S) for l in range(L)]
    raise ValueError(code)


def build_class_sequences(K,scode):
    C,L,S,T=K.shape
    if C!=3:raise RuntimeError('mask-class codec requires 3 components')
    sites=site_order(L,S,scode);counts=np.zeros((7,len(sites)),np.uint16);gaps_by=[[] for _ in range(7)];vals=[]
    for j,(l,s) in enumerate(sites):
        A=K[:,l,s,:]
        mask=(A[0]!=0).astype(np.uint8)|((A[1]!=0).astype(np.uint8)<<1)|((A[2]!=0).astype(np.uint8)<<2)
        for mi,m in enumerate(range(1,8)):
            pos=np.flatnonzero(mask==m);counts[mi,j]=pos.size
            if not pos.size:continue
            g=np.empty(pos.size,np.int32);g[0]=pos[0]+1
            if pos.size>1:g[1:]=np.diff(pos)
            gaps_by[mi].extend(g.tolist());comps=[c for c in range(3) if m&(1<<c)]
            for t in pos.tolist():
                for c in comps:vals.append(int(A[c,t]))
    gaps_by=[np.asarray(x,np.int32) for x in gaps_by];vals=np.asarray(vals,np.int32)
    cev=[int(counts[i].sum()) for i in range(7)];cvv=[cev[m-1]*int(((m&1)>0)+((m&2)>0)+((m&4)>0)) for m in range(1,8)]
    return counts,gaps_by,vals,cev,cvv


def encode7(K,scode,valmode,level,split):
    zc=zstd.ZstdCompressor(level=level);counts,gby,vals,cev,cvv=build_class_sequences(K,scode);frames=[]
    if split:
        for mi in range(7):
            frames.append(zc.compress(counts[mi].astype('<u2',copy=False).tobytes()))
            frames.append(zc.compress(leb128_u(gby[mi])))
        timing_n=14
    else:
        frames=[zc.compress(counts.astype('<u2',copy=False).tobytes()),zc.compress(leb128_u(np.concatenate(gby) if sum(x.size for x in gby) else np.empty(0,np.int32)))]
        timing_n=2
    dc=1
    if valmode==0:
        dc=dtype_code(vals);v1=zc.compress(vals.astype(DT[dc],copy=False).tobytes());v2=zc.compress(b'');v3=zc.compress(b'')
    else:
        sign=vals<0;ab=np.abs(vals);exc=ab!=1
        v1=zc.compress(np.packbits(sign,bitorder='little').tobytes());v2=zc.compress(np.packbits(exc,bitorder='little').tobytes());mag=(ab[exc]-2).astype(np.int32);dc=dtype_code(mag);v3=zc.compress(mag.astype(DT[dc],copy=False).tobytes()) if mag.size else zc.compress(b'')
    frames += [v1,v2,v3];nf=len(frames);lens=[len(x) for x in frames]
    h=struct.pack(H7,MAG7,1,int(scode),int(valmode),int(split),int(dc),*K.shape,nf);lb=b''.join(struct.pack('<Q',n) for n in lens)
    parts={'timing_mode':'split7' if split else 'combined','site_order':'LS' if scode==0 else 'SL','timing_bytes':sum(lens[:timing_n]),'counts_bytes':sum(lens[0:timing_n:2]) if split else lens[0],'gaps_bytes':sum(lens[1:timing_n:2]) if split else lens[1],'v1':len(v1),'v2':len(v2),'v3':len(v3),'union_events':sum(cev),'component_values':int(vals.size),'class_events':cev,'class_component_values':cvv,'counts_nonzero':int(np.count_nonzero(counts)),'raw_varint_bytes':sum(len(leb128_u(x)) for x in gby),'frame_lengths_bytes':len(lb)}
    return h+lb+b''.join(frames),parts


def decode7(blob):
    magic,ver,scode,valmode,split,dc,C,L,S,T,nf=struct.unpack(H7,blob[:H7S])
    if magic!=MAG7 or ver!=1 or C!=3:raise RuntimeError('maskclass header')
    p=H7S;lens=[]
    for _ in range(nf):lens.append(struct.unpack('<Q',blob[p:p+8])[0]);p+=8
    frames=[]
    for n in lens:frames.append(blob[p:p+n]);p+=n
    if p!=len(blob):raise RuntimeError('maskclass length')
    zd=zstd.ZstdDecompressor();sites=site_order(L,S,scode);nsites=len(sites)
    if not split:
        if nf!=5:raise RuntimeError(('combined frame count',nf))
        counts=np.frombuffer(zd.decompress(frames[0]),'<u2',count=7*nsites).astype(np.int32).reshape(7,nsites);ne=int(counts.sum());gaps=leb128_decode(zd.decompress(frames[1]),ne);vn=2
    else:
        if nf!=17:raise RuntimeError(('split frame count',nf))
        counts=np.empty((7,nsites),np.int32);gg=[]
        for mi in range(7):
            counts[mi]=np.frombuffer(zd.decompress(frames[2*mi]),'<u2',count=nsites).astype(np.int32);ne=int(counts[mi].sum());gg.extend(leb128_decode(zd.decompress(frames[2*mi+1]),ne).tolist())
        gaps=np.asarray(gg,np.int32);vn=14
    nvals=sum(int(counts[m-1].sum())*int(((m&1)>0)+((m&2)>0)+((m&4)>0)) for m in range(1,8));v1,v2,v3=frames[vn:vn+3]
    if valmode==0:
        vals=np.frombuffer(zd.decompress(v1),dtype=DT[dc],count=nvals).astype(np.int32)
    else:
        sign=np.unpackbits(np.frombuffer(zd.decompress(v1),np.uint8),bitorder='little',count=nvals).astype(bool);exc=np.unpackbits(np.frombuffer(zd.decompress(v2),np.uint8),bitorder='little',count=nvals).astype(bool);ab=np.ones(nvals,np.int32)
        if exc.any():ab[exc]=np.frombuffer(zd.decompress(v3),dtype=DT[dc],count=int(exc.sum())).astype(np.int32)+2
        vals=np.where(sign,-ab,ab)
    K=np.zeros((3,L,S,T),np.int32);kg=0;kv=0
    for mi,m in enumerate(range(1,8)):
        comps=[c for c in range(3) if m&(1<<c)]
        for j,(l,s) in enumerate(sites):
            c=int(counts[mi,j])
            if not c:continue
            g=gaps[kg:kg+c];kg+=c;pos=np.cumsum(g)-1
            if pos[-1]>=T:raise RuntimeError('class position')
            for t in pos.tolist():
                for cc in comps:K[cc,l,s,t]=vals[kv];kv+=1
    if kg!=gaps.size or kv!=vals.size:raise RuntimeError(('decode accounting',kg,gaps.size,kv,vals.size))
    return K


def best_outlier(O):
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
    for scode in (0,1):
        for vm in (0,1):
            for level in (19,22):
                for split in (False,True):
                    b,parts=encode7(K,scode,vm,level,split);R=decode7(b)
                    if not np.array_equal(R,K):raise RuntimeError(('maskclass integer decode',scode,vm,level,split))
                    rows.append((len(b),scode,vm,level,split,b,parts))
    rows.sort(key=lambda x:x[0]);bm=rows[0];bo=best_outlier(O)
    topfmt='<8sdQQB';top=struct.pack(topfmt,b'MC7TOP02',eps,len(bm[5]),len(bo[6]),0 if bo[1]=='gap' else 1)+bm[5]+bo[6];hs=struct.calcsize(topfmt);_,ee,lm,lo,ok=struct.unpack(topfmt,top[:hs]);RK=decode7(top[hs:hs+lm]);obb=top[hs+lm:hs+lm+lo]
    if ok==0:
        A=decode(obb).reshape(O.shape);RO=undelta(A,1) if bo[2] else A
    else:
        A=decode_out_sparse(obb);RO=undelta(A,1) if bo[2] else A
    RG=undelta(RK,3);Y=np.empty_like(X)
    for tid,c,l,s in tm:Y[tid]=RG[c,l,s].astype(np.float32)*np.float32(2*ee)
    Y[outids]=RO.astype(np.float32)*np.float32(2*ee);me=float(np.max(np.abs(X-Y)));szb,sze=sz3_bytes(X,eps)
    cands=[{'bytes':r[0],'site_order':'LS' if r[1]==0 else 'SL','value_mode':'signed' if r[2]==0 else 'signmag','level':r[3],'timing_mode':'split7' if r[4] else 'combined','parts':r[6]} for r in rows]
    outmeta={'bytes':bo[0],'kind':bo[1],'tdiff':bo[2],'mode':bo[3],'level':bo[4],'perm':list(bo[5]) if bo[5] is not None else None,'parts':bo[7]}
    out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'eps':eps,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'main_best':cands[0],'main_candidates':cands,'outlier_best':outmeta,'container_bytes':len(top),'ratio':raw/len(top),'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'sz3':{'bytes':szb,'ratio':raw/szb,'maxerr':sze},'gain_vs_direct_sz3':szb/len(top),'strongest_verified_p75_baseline_bytes':133225,'gain_vs_strongest_verified_p75_baseline':133225/len(top),'two_x_gate_bytes':133225/2,'prior_event_gap_frontier_bytes':70208}
    print(json.dumps(out,indent=2),flush=True);json.dump(out,open('soda_maskclass_event_gap.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
