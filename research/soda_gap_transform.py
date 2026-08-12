import itertools,json,os,struct,sys
import numpy as np
import zstandard as zstd

# Reuse audited Soda geometry, PR #126 event-gap outlier codec, and sparse helpers.
src=open('research/soda_event_gap.py').read().split('\npath=sys.argv[1]')[0]
exec(compile(src,'soda_event_gap.py','exec'),globals())

GMAG=b'GTRNv001'; GHDR='<8sBBBBB4I7Q'; GHS=struct.calcsize(GHDR)


def zzenc(x):
    x=np.asarray(x,np.int64);return ((x<<1)^(x>>63)).astype(np.uint64)
def zzdec(u):
    u=np.asarray(u,np.int64);return ((u>>1)^(-(u&1))).astype(np.int32)

def leb128_u64(values):
    out=bytearray()
    for vv in values:
        v=int(vv)
        while v>=128:out.append((v&127)|128);v>>=7
        out.append(v)
    return bytes(out)

def leb128_decode_u64(data,n):
    out=np.empty(n,np.uint64);j=0;v=0;shift=0
    for b in data:
        v|=(b&127)<<shift
        if not (b&128):
            if j>=n:raise RuntimeError('too many gap varints')
            out[j]=v;j+=1;v=0;shift=0
        else:shift+=7
    if j!=n or shift:raise RuntimeError(('gap varint count',j,n,shift))
    return out


def gather(K,order):
    P=np.transpose(K,order+(3,));sh=P.shape;tr=P.reshape(-1,sh[-1]);counts=np.count_nonzero(tr,axis=1).astype(np.uint16);gaps=[];vals=[]
    for row in tr:
        pos=np.flatnonzero(row)
        if not pos.size:continue
        g=np.empty(pos.size,np.int32);g[0]=pos[0]+1
        if pos.size>1:g[1:]=np.diff(pos)
        gaps.extend(g.tolist());vals.extend(row[pos].astype(np.int32).tolist())
    return P.shape,counts,np.asarray(gaps,np.int32),np.asarray(vals,np.int32)


def gap_delta(gaps,counts):
    d=np.empty_like(gaps);k=0
    for c0 in counts.tolist():
        c=int(c0)
        if not c:continue
        g=gaps[k:k+c];d[k]=g[0]
        if c>1:d[k+1:k+c]=g[1:]-g[:-1]
        k+=c
    if k!=gaps.size:raise RuntimeError('delta gap count')
    return d

def gap_undelta(d,counts):
    g=np.empty_like(d);k=0
    for c0 in counts.tolist():
        c=int(c0)
        if not c:continue
        q=d[k:k+c];g[k]=q[0]
        if c>1:g[k+1:k+c]=q[0]+np.cumsum(q[1:],dtype=np.int32)
        k+=c
    if k!=d.size:raise RuntimeError('undelta gap count')
    return g


def med_residual(gaps,counts):
    med=[];r=np.empty_like(gaps);k=0
    for c0 in counts.tolist():
        c=int(c0)
        if not c:continue
        g=gaps[k:k+c];m=int(np.median(g));med.append(m);r[k:k+c]=g-m;k+=c
    if k!=gaps.size:raise RuntimeError('median gap count')
    return np.asarray(med,np.uint16),r

def unmed_residual(med,r,counts):
    g=np.empty_like(r);k=0;j=0
    for c0 in counts.tolist():
        c=int(c0)
        if not c:continue
        g[k:k+c]=r[k:k+c]+int(med[j]);j+=1;k+=c
    if k!=r.size or j!=med.size:raise RuntimeError('median decode count')
    return g


def encode_gap_frames(gaps,counts,mode,zc):
    aux=b'';diag={'gap_mode':mode,'events':int(gaps.size),'gap_min':int(gaps.min()) if gaps.size else 0,'gap_max':int(gaps.max()) if gaps.size else 0}
    if mode==0:
        raw=leb128_u(gaps);gb=zc.compress(raw);diag.update({'name':'raw-varint','raw_bytes':len(raw)})
    elif mode==1:
        d=gap_delta(gaps,counts);raw=leb128_u64(zzenc(d));gb=zc.compress(raw);diag.update({'name':'delta-zigzag-varint','raw_bytes':len(raw),'delta_abs_mean':float(np.mean(np.abs(d))) if d.size else 0})
    elif mode==2:
        if gaps.size and int(gaps.max())>65535:raise RuntimeError('gap exceeds uint16')
        raw=gaps.astype('<u2',copy=False).tobytes();gb=zc.compress(raw);diag.update({'name':'uint16','raw_bytes':len(raw)})
    elif mode==3:
        d=gap_delta(gaps,counts)
        if d.size and (int(d.min())<-32768 or int(d.max())>32767):raise RuntimeError('gap delta exceeds int16')
        raw=d.astype('<i2',copy=False).tobytes();gb=zc.compress(raw);diag.update({'name':'delta-int16','raw_bytes':len(raw),'delta_abs_mean':float(np.mean(np.abs(d))) if d.size else 0})
    elif mode in (4,5):
        med,r=med_residual(gaps,counts);aux=zc.compress(med.astype('<u2',copy=False).tobytes())
        if mode==4:
            raw=leb128_u64(zzenc(r));gb=zc.compress(raw);diag.update({'name':'median-zigzag-varint','raw_bytes':len(raw)})
        else:
            if r.size and (int(r.min())<-32768 or int(r.max())>32767):raise RuntimeError('median residual exceeds int16')
            raw=r.astype('<i2',copy=False).tobytes();gb=zc.compress(raw);diag.update({'name':'median-int16','raw_bytes':len(raw)})
        diag['median_bytes']=len(aux);diag['median_count']=int(med.size)
    else:raise ValueError(mode)
    diag['aux_bytes']=len(aux);diag['gap_bytes']=len(gb);return aux,gb,diag


def decode_gap_frames(auxb,gb,counts,mode,zd):
    ne=int(counts.sum())
    if mode==0:gaps=leb128_decode(zd.decompress(gb),ne)
    elif mode==1:
        d=zzdec(leb128_decode_u64(zd.decompress(gb),ne));gaps=gap_undelta(d,counts)
    elif mode==2:gaps=np.frombuffer(zd.decompress(gb),'<u2',count=ne).astype(np.int32)
    elif mode==3:
        d=np.frombuffer(zd.decompress(gb),'<i2',count=ne).astype(np.int32);gaps=gap_undelta(d,counts)
    elif mode in (4,5):
        nm=int(np.count_nonzero(counts));med=np.frombuffer(zd.decompress(auxb),'<u2',count=nm).astype(np.int32)
        if mode==4:r=zzdec(leb128_decode_u64(zd.decompress(gb),ne))
        else:r=np.frombuffer(zd.decompress(gb),'<i2',count=ne).astype(np.int32)
        gaps=unmed_residual(med,r,counts)
    else:raise ValueError(mode)
    if gaps.size and np.any(gaps<=0):raise RuntimeError(('nonpositive decoded gap',mode,int(gaps.min())))
    return gaps


def sign_alt_planes(vals,counts):
    signs=vals<0;first=[];repeat=[];k=0;rep_count=0;transitions=0
    for c0 in counts.tolist():
        c=int(c0)
        if not c:continue
        s=signs[k:k+c];first.append(int(s[0]))
        if c>1:
            r=(s[1:]==s[:-1]);repeat.extend(r.astype(np.uint8).tolist());rep_count+=int(r.sum());transitions+=c-1
        k+=c
    if k!=vals.size:raise RuntimeError('sign count')
    return np.asarray(first,np.uint8),np.asarray(repeat,np.uint8),{'nonempty_traces':len(first),'repeat_sign_count':rep_count,'sign_transitions':transitions,'repeat_sign_fraction':rep_count/max(1,transitions)}


def encode_main(K,order,gmode,smode,level):
    zc=zstd.ZstdCompressor(level=level);psh,counts,gaps,vals=gather(K,order);cb=zc.compress(counts.astype('<u2',copy=False).tobytes());aux,gb,gdiag=encode_gap_frames(gaps,counts,gmode,zc);ab=np.abs(vals);exc=ab!=1;mag=(ab[exc]-2).astype(np.int32);dc=dtype_code(mag)
    if smode==0:
        s1=zc.compress(np.packbits(vals<0,bitorder='little').tobytes());s2=zc.compress(b'');sdiag={'sign_mode':'raw'}
    else:
        first,repeat,sdiag=sign_alt_planes(vals,counts);s1=zc.compress(np.packbits(first,bitorder='little').tobytes());s2=zc.compress(np.packbits(repeat,bitorder='little').tobytes());sdiag['sign_mode']='alternate-residual'
    eb=zc.compress(np.packbits(exc,bitorder='little').tobytes());mb=zc.compress(mag.astype(DT[dc],copy=False).tobytes()) if mag.size else zc.compress(b'');oc=int(order[0]|(order[1]<<2)|(order[2]<<4));h=struct.pack(GHDR,GMAG,1,oc,gmode,smode,dc,*K.shape,len(cb),len(aux),len(gb),len(s1),len(s2),len(eb),len(mb));parts={'counts':len(cb),'aux':len(aux),'gaps':len(gb),'sign1':len(s1),'sign2':len(s2),'exception_support':len(eb),'exception_magnitude':len(mb),'events':int(vals.size),**gdiag,**sdiag};return h+cb+aux+gb+s1+s2+eb+mb,parts


def decode_main(blob):
    q=struct.unpack(GHDR,blob[:GHS]);magic,ver,oc,gmode,smode,dc,C,L,S,T,lc,la,lg,l1,l2,le,lm=q
    if magic!=GMAG or ver!=1:raise RuntimeError('gap-transform header')
    p=GHS;cb=blob[p:p+lc];p+=lc;aux=blob[p:p+la];p+=la;gb=blob[p:p+lg];p+=lg;s1=blob[p:p+l1];p+=l1;s2=blob[p:p+l2];p+=l2;eb=blob[p:p+le];p+=le;mb=blob[p:p+lm];p+=lm
    if p!=len(blob):raise RuntimeError('gap-transform length')
    order=tuple((oc>>(2*i))&3 for i in range(3));shape=(C,L,S,T);psh=tuple(shape[i] for i in order)+(T,);ntr=int(np.prod(psh[:-1]));zd=zstd.ZstdDecompressor();counts=np.frombuffer(zd.decompress(cb),'<u2',count=ntr).astype(np.int32);ne=int(counts.sum());gaps=decode_gap_frames(aux,gb,counts,gmode,zd)
    if smode==0:signs=np.unpackbits(np.frombuffer(zd.decompress(s1),np.uint8),bitorder='little',count=ne).astype(bool)
    else:
        nn=int(np.count_nonzero(counts));nr=ne-nn;first=np.unpackbits(np.frombuffer(zd.decompress(s1),np.uint8),bitorder='little',count=nn).astype(bool);repeat=np.unpackbits(np.frombuffer(zd.decompress(s2),np.uint8),bitorder='little',count=nr).astype(bool);signs=np.empty(ne,bool);k=fk=rk=0
        for c0 in counts.tolist():
            c=int(c0)
            if not c:continue
            s=bool(first[fk]);fk+=1;signs[k]=s;k+=1
            for _ in range(1,c):
                if not repeat[rk]:s=not s
                rk+=1;signs[k]=s;k+=1
        if k!=ne or fk!=nn or rk!=nr:raise RuntimeError('sign decode accounting')
    exc=np.unpackbits(np.frombuffer(zd.decompress(eb),np.uint8),bitorder='little',count=ne).astype(bool);ab=np.ones(ne,np.int32)
    if exc.any():ab[exc]=np.frombuffer(zd.decompress(mb),dtype=DT[dc],count=int(exc.sum())).astype(np.int32)+2
    vals=np.where(signs,-ab,ab);tr=np.zeros((ntr,T),np.int32);k=0
    for i,c0 in enumerate(counts.tolist()):
        c=int(c0)
        if not c:continue
        g=gaps[k:k+c];pos=np.cumsum(g)-1
        if pos[-1]>=T:raise RuntimeError(('event position',int(pos[-1]),T,gmode))
        tr[i,pos]=vals[k:k+c];k+=c
    if k!=ne:raise RuntimeError('event count decode')
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
        for gm in range(6):
            for sm in (0,1):
                for level in (19,22):
                    b,parts=encode_main(K,order,gm,sm,level);R=decode_main(b)
                    if not np.array_equal(R,K):raise RuntimeError(('gap transform K decode',order,gm,sm,level))
                    rows.append((len(b),order,gm,sm,level,b,parts))
    rows.sort(key=lambda x:x[0]);bm=rows[0];bo=best_out(O);topfmt='<8sdQQB';top=struct.pack(topfmt,b'GTOPv001',eps,len(bm[5]),len(bo[6]),0 if bo[1]=='gap' else 1)+bm[5]+bo[6];hs=struct.calcsize(topfmt);_,ee,lm,lo,ok=struct.unpack(topfmt,top[:hs]);RK=decode_main(top[hs:hs+lm]);obb=top[hs+lm:hs+lm+lo]
    if ok==0:
        A=decode(obb).reshape(O.shape);RO=undelta(A,1) if bo[2] else A
    else:
        A=decode_out_sparse(obb);RO=undelta(A,1) if bo[2] else A
    RG=undelta(RK,3);Y=np.empty_like(X)
    for tid,c,l,s in tm:Y[tid]=RG[c,l,s].astype(np.float32)*np.float32(2*ee)
    Y[outids]=RO.astype(np.float32)*np.float32(2*ee);me=float(np.max(np.abs(X-Y)));szb,sze=sz3_bytes(X,eps)
    names=['raw-varint','delta-zigzag-varint','uint16','delta-int16','median-zigzag-varint','median-int16'];cands=[{'bytes':r[0],'order':list(r[1]),'gap_mode':names[r[2]],'sign_mode':'raw' if r[3]==0 else 'alternate-residual','level':r[4],'parts':r[6]} for r in rows[:30]];outmeta={'bytes':bo[0],'kind':bo[1],'tdiff':bo[2],'mode':bo[3],'level':bo[4],'perm':list(bo[5]) if bo[5] is not None else None,'parts':bo[7]}
    out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'eps':eps,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'main_best':cands[0],'main_candidates':cands,'outlier_best':outmeta,'container_bytes':len(top),'ratio':raw/len(top),'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'sz3':{'bytes':szb,'ratio':raw/szb,'maxerr':sze},'gain_vs_direct_sz3':szb/len(top),'strongest_verified_p75_baseline_bytes':133225,'gain_vs_strongest_verified_p75_baseline':133225/len(top),'two_x_gate_bytes':133225/2,'prior_record_bytes':70114}
    print(json.dumps(out,indent=2),flush=True);json.dump(out,open('soda_gap_transform.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
