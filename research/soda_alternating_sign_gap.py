import itertools,json,os,struct,sys
import numpy as np
import zstandard as zstd

# Reuse audited Soda geometry, lattice, varints, and outlier helpers.
src=open('research/soda_event_gap.py').read().split('\npath=sys.argv[1]')[0]
exec(compile(src,'soda_event_gap.py','exec'),globals())

MAG=b'ASGNv001'; HDR='<8sBBBB4I6Q'; HS=struct.calcsize(HDR)


def sign_alt_planes(vals,counts):
    signs=vals<0;first=[];repeat=[];k=0;rep_count=0;transitions=0
    for c0 in counts.tolist():
        c=int(c0)
        if not c:continue
        s=signs[k:k+c];first.append(int(s[0]))
        if c>1:
            r=(s[1:]==s[:-1]);repeat.extend(r.astype(np.uint8).tolist());rep_count+=int(r.sum());transitions+=c-1
        k+=c
    if k!=vals.size:raise RuntimeError('sign plane count')
    return np.asarray(first,np.uint8),np.asarray(repeat,np.uint8),{'nonempty_traces':len(first),'sign_transitions':transitions,'repeat_sign_count':rep_count,'repeat_sign_fraction':rep_count/max(1,transitions)}


def encode_alt(K,order,level,smode):
    zc=zstd.ZstdCompressor(level=level);P=np.transpose(K,order+(3,));sh=P.shape;tr=P.reshape(-1,sh[-1]);counts=np.count_nonzero(tr,axis=1).astype(np.uint16);gaps=[];vals=[]
    for row in tr:
        pos=np.flatnonzero(row)
        if pos.size:
            g=np.empty(pos.size,np.int32);g[0]=pos[0]+1
            if pos.size>1:g[1:]=np.diff(pos)
            gaps.extend(g.tolist());vals.extend(row[pos].astype(np.int32).tolist())
    gaps=np.asarray(gaps,np.int32);vals=np.asarray(vals,np.int32);ab=np.abs(vals);exc=ab!=1;mag=(ab[exc]-2).astype(np.int32);dc=dtype_code(mag)
    cb=zc.compress(counts.astype('<u2',copy=False).tobytes());gb=zc.compress(leb128_u(gaps));diag={}
    if smode==0:
        sb=zc.compress(np.packbits(vals<0,bitorder='little').tobytes());rb=zc.compress(b'');diag={'sign_mode':'raw','nonempty_traces':int(np.count_nonzero(counts))}
    else:
        first,repeat,diag=sign_alt_planes(vals,counts);sb=zc.compress(np.packbits(first,bitorder='little').tobytes());rb=zc.compress(np.packbits(repeat,bitorder='little').tobytes());diag['sign_mode']='alternate-residual'
    eb=zc.compress(np.packbits(exc,bitorder='little').tobytes());mb=zc.compress(mag.astype(DT[dc],copy=False).tobytes()) if mag.size else zc.compress(b'')
    oc=int(order[0]|(order[1]<<2)|(order[2]<<4));h=struct.pack(HDR,MAG,1,oc,smode,dc,*K.shape,len(cb),len(gb),len(sb),len(rb),len(eb),len(mb));parts={'counts':len(cb),'gaps':len(gb),'sign_first_or_raw':len(sb),'sign_repeat':len(rb),'exception_support':len(eb),'exception_magnitude':len(mb),'events':int(vals.size),'raw_varint_bytes':len(leb128_u(gaps)),**diag};return h+cb+gb+sb+rb+eb+mb,parts


def decode_alt(blob):
    q=struct.unpack(HDR,blob[:HS]);magic,ver,oc,smode,dc,C,L,S,T,lc,lg,ls,lr,le,lm=q
    if magic!=MAG or ver!=1:raise RuntimeError('alt-sign header')
    p=HS;cb=blob[p:p+lc];p+=lc;gb=blob[p:p+lg];p+=lg;sb=blob[p:p+ls];p+=ls;rb=blob[p:p+lr];p+=lr;eb=blob[p:p+le];p+=le;mb=blob[p:p+lm];p+=lm
    if p!=len(blob):raise RuntimeError('alt-sign length')
    order=tuple((oc>>(2*i))&3 for i in range(3));shape=(C,L,S,T);psh=tuple(shape[i] for i in order)+(T,);ntr=int(np.prod(psh[:-1]));zd=zstd.ZstdDecompressor();counts=np.frombuffer(zd.decompress(cb),'<u2',count=ntr).astype(np.int32);ne=int(counts.sum());gaps=leb128_decode(zd.decompress(gb),ne)
    if smode==0:
        signs=np.unpackbits(np.frombuffer(zd.decompress(sb),np.uint8),bitorder='little',count=ne).astype(bool)
    else:
        nnztr=int(np.count_nonzero(counts));nrep=ne-nnztr;first=np.unpackbits(np.frombuffer(zd.decompress(sb),np.uint8),bitorder='little',count=nnztr).astype(bool);repeat=np.unpackbits(np.frombuffer(zd.decompress(rb),np.uint8),bitorder='little',count=nrep).astype(bool);signs=np.empty(ne,bool);k=fk=rk=0
        for c0 in counts.tolist():
            c=int(c0)
            if not c:continue
            s=bool(first[fk]);fk+=1;signs[k]=s;k+=1
            for _ in range(1,c):
                if not repeat[rk]:s=not s
                rk+=1;signs[k]=s;k+=1
        if k!=ne or fk!=nnztr or rk!=nrep:raise RuntimeError('alt sign accounting')
    exc=np.unpackbits(np.frombuffer(zd.decompress(eb),np.uint8),bitorder='little',count=ne).astype(bool);ab=np.ones(ne,np.int32)
    if exc.any():ab[exc]=np.frombuffer(zd.decompress(mb),dtype=DT[dc],count=int(exc.sum())).astype(np.int32)+2
    vals=np.where(signs,-ab,ab);tr=np.zeros((ntr,T),np.int32);k=0
    for i,c0 in enumerate(counts.tolist()):
        c=int(c0)
        if not c:continue
        g=gaps[k:k+c];pos=np.cumsum(g)-1
        if pos[-1]>=T:raise RuntimeError('alt-sign position')
        tr[i,pos]=vals[k:k+c];k+=c
    if k!=ne:raise RuntimeError('alt value accounting')
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
            for smode in (0,1):
                b,parts=encode_alt(K,order,level,smode);R=decode_alt(b)
                if not np.array_equal(R,K):raise RuntimeError(('alt-sign decode',order,level,smode))
                rows.append((len(b),order,level,smode,b,parts))
    rows.sort(key=lambda x:x[0]);bm=rows[0];bo=best_out(O);topfmt='<8sdQQB';top=struct.pack(topfmt,b'ASTOP001',eps,len(bm[4]),len(bo[6]),0 if bo[1]=='gap' else 1)+bm[4]+bo[6];hs=struct.calcsize(topfmt);_,ee,lm,lo,ok=struct.unpack(topfmt,top[:hs]);RK=decode_alt(top[hs:hs+lm]);obb=top[hs+lm:hs+lm+lo]
    if ok==0:
        A=decode(obb).reshape(O.shape);RO=undelta(A,1) if bo[2] else A
    else:
        A=decode_out_sparse(obb);RO=undelta(A,1) if bo[2] else A
    RG=undelta(RK,3);Y=np.empty_like(X)
    for tid,c,l,s in tm:Y[tid]=RG[c,l,s].astype(np.float32)*np.float32(2*ee)
    Y[outids]=RO.astype(np.float32)*np.float32(2*ee);me=float(np.max(np.abs(X-Y)));szb,sze=sz3_bytes(X,eps)
    cands=[{'bytes':r[0],'order':list(r[1]),'level':r[2],'sign_mode':'raw' if r[3]==0 else 'alternate-residual','parts':r[5]} for r in rows];outmeta={'bytes':bo[0],'kind':bo[1],'tdiff':bo[2],'mode':bo[3],'level':bo[4],'perm':list(bo[5]) if bo[5] is not None else None,'parts':bo[7]}
    out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'eps':eps,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'main_best':cands[0],'main_candidates':cands,'outlier_best':outmeta,'container_bytes':len(top),'ratio':raw/len(top),'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'sz3':{'bytes':szb,'ratio':raw/szb,'maxerr':sze},'gain_vs_direct_sz3':szb/len(top),'strongest_verified_p75_baseline_bytes':133225,'gain_vs_strongest_verified_p75_baseline':133225/len(top),'two_x_gate_bytes':133225/2,'prior_event_gap_frontier_bytes':70208}
    print(json.dumps(out,indent=2),flush=True);json.dump(out,open('soda_alternating_sign_gap.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
