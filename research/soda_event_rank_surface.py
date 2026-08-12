import itertools,json,os,struct,sys
import numpy as np
import zstandard as zstd

# Reuse audited Soda geometry, PR #126 outlier codec, varints, sparse helpers.
src=open('research/soda_event_gap.py').read().split('\npath=sys.argv[1]')[0]
exec(compile(src,'soda_event_gap.py','exec'),globals())

EMAG=b'ERKSv001'; EHDR='<8sBBBB4I7Q'; EHS=struct.calcsize(EHDR)


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
            if j>=n:raise RuntimeError('too many varints')
            out[j]=v;j+=1;v=0;shift=0
        else:shift+=7
    if j!=n or shift:raise RuntimeError(('varint count',j,n,shift))
    return out


def sign_alt_planes(vals,counts):
    signs=vals<0;first=[];repeat=[];k=0;rep=0;trans=0
    for c0 in counts.tolist():
        c=int(c0)
        if not c:continue
        s=signs[k:k+c];first.append(int(s[0]))
        if c>1:
            r=(s[1:]==s[:-1]);repeat.extend(r.astype(np.uint8).tolist());rep+=int(r.sum());trans+=c-1
        k+=c
    if k!=vals.size:raise RuntimeError('sign count')
    return np.asarray(first,np.uint8),np.asarray(repeat,np.uint8),{'repeat_sign_fraction':rep/max(1,trans),'repeat_sign_count':rep,'sign_transitions':trans,'nonempty_traces':len(first)}


def gather(K,order):
    P=np.transpose(K,order+(3,));sh=P.shape;tr=P.reshape(-1,sh[-1]);counts=np.count_nonzero(tr,axis=1).astype(np.uint16);posrows=[];gaprows=[];vals=[]
    for row in tr:
        pos=np.flatnonzero(row).astype(np.int32);posrows.append(pos)
        if pos.size:
            g=np.empty(pos.size,np.int32);g[0]=pos[0]+1
            if pos.size>1:g[1:]=np.diff(pos)
            gaprows.append(g);vals.extend(row[pos].astype(np.int32).tolist())
        else:gaprows.append(np.empty(0,np.int32))
    return sh,counts,posrows,gaprows,np.asarray(vals,np.int32)


def rank_sequence(rows,counts,delta=False):
    out=[];maxc=int(counts.max()) if counts.size else 0
    for r in range(maxc):
        q=[int(rows[i][r]) for i in range(len(rows)) if int(counts[i])>r]
        if not q:continue
        if delta:
            out.append(q[0])
            for j in range(1,len(q)):out.append(q[j]-q[j-1])
        else:out.extend(q)
    return np.asarray(out,np.int32)


def trace_gap_sequence(gaprows):
    return np.concatenate(gaprows) if gaprows and sum(x.size for x in gaprows) else np.empty(0,np.int32)


def encode_timing(posrows,gaprows,counts,mode,zc):
    ne=int(counts.sum());diag={'mode':mode,'events':ne,'max_count':int(counts.max()) if counts.size else 0}
    if mode==0:
        seq=trace_gap_sequence(gaprows);raw=leb128_u(seq);tb=zc.compress(raw);diag.update({'name':'trace-gap-varint','raw_bytes':len(raw)})
    elif mode==1:
        seq=rank_sequence(posrows,counts,False)
        if seq.size!=ne:raise RuntimeError('rank pos count')
        raw=seq.astype('<u2',copy=False).tobytes();tb=zc.compress(raw);diag.update({'name':'rank-position-uint16','raw_bytes':len(raw)})
    elif mode==2:
        seq=rank_sequence(posrows,counts,True)
        if seq.size!=ne or (seq.size and (int(seq.min())<-32768 or int(seq.max())>32767)):raise RuntimeError('rank pos delta range')
        raw=seq.astype('<i2',copy=False).tobytes();tb=zc.compress(raw);diag.update({'name':'rank-position-delta-int16','raw_bytes':len(raw),'delta_abs_mean':float(np.mean(np.abs(seq))) if seq.size else 0})
    elif mode==3:
        seq=rank_sequence(posrows,counts,True);raw=leb128_u64(zzenc(seq));tb=zc.compress(raw);diag.update({'name':'rank-position-delta-zigzag','raw_bytes':len(raw),'delta_abs_mean':float(np.mean(np.abs(seq))) if seq.size else 0})
    elif mode==4:
        seq=rank_sequence(gaprows,counts,False);raw=leb128_u(seq);tb=zc.compress(raw);diag.update({'name':'rank-gap-varint','raw_bytes':len(raw)})
    elif mode==5:
        seq=rank_sequence(gaprows,counts,True);raw=leb128_u64(zzenc(seq));tb=zc.compress(raw);diag.update({'name':'rank-gap-delta-zigzag','raw_bytes':len(raw),'delta_abs_mean':float(np.mean(np.abs(seq))) if seq.size else 0})
    elif mode==6:
        seq=rank_sequence(gaprows,counts,True)
        if seq.size and (int(seq.min())<-32768 or int(seq.max())>32767):raise RuntimeError('rank gap delta range')
        raw=seq.astype('<i2',copy=False).tobytes();tb=zc.compress(raw);diag.update({'name':'rank-gap-delta-int16','raw_bytes':len(raw),'delta_abs_mean':float(np.mean(np.abs(seq))) if seq.size else 0})
    else:raise ValueError(mode)
    diag['timing_bytes']=len(tb);return tb,diag


def distribute_rank(seq,counts,delta=False):
    rows=[np.empty(int(c),np.int32) for c in counts.tolist()];k=0;maxc=int(counts.max()) if counts.size else 0
    for r in range(maxc):
        active=[i for i,c in enumerate(counts.tolist()) if int(c)>r]
        if not active:continue
        prev=0
        for j,i in enumerate(active):
            v=int(seq[k]);k+=1
            if delta:
                if j==0:q=v
                else:q=prev+v
                prev=q
            else:q=v
            rows[i][r]=q
    if k!=seq.size:raise RuntimeError(('rank distribute',k,seq.size))
    return rows


def decode_timing(tb,counts,mode,zd):
    ne=int(counts.sum())
    if mode==0:
        gaps=leb128_decode(zd.decompress(tb),ne);rows=[];k=0
        for c0 in counts.tolist():
            c=int(c0);g=gaps[k:k+c];k+=c;rows.append((np.cumsum(g)-1).astype(np.int32) if c else np.empty(0,np.int32))
        if k!=ne:raise RuntimeError('trace gap decode')
        return rows
    if mode==1:seq=np.frombuffer(zd.decompress(tb),'<u2',count=ne).astype(np.int32);return distribute_rank(seq,counts,False)
    if mode==2:seq=np.frombuffer(zd.decompress(tb),'<i2',count=ne).astype(np.int32);return distribute_rank(seq,counts,True)
    if mode==3:seq=zzdec(leb128_decode_u64(zd.decompress(tb),ne));return distribute_rank(seq,counts,True)
    if mode==4:
        seq=leb128_decode(zd.decompress(tb),ne);grows=distribute_rank(seq,counts,False);return [(np.cumsum(g)-1).astype(np.int32) if g.size else g for g in grows]
    if mode==5:
        seq=zzdec(leb128_decode_u64(zd.decompress(tb),ne));grows=distribute_rank(seq,counts,True);return [(np.cumsum(g)-1).astype(np.int32) if g.size else g for g in grows]
    if mode==6:
        seq=np.frombuffer(zd.decompress(tb),'<i2',count=ne).astype(np.int32);grows=distribute_rank(seq,counts,True);return [(np.cumsum(g)-1).astype(np.int32) if g.size else g for g in grows]
    raise ValueError(mode)


def encode_main(K,order,mode,level):
    zc=zstd.ZstdCompressor(level=level);sh,counts,posrows,gaprows,vals=gather(K,order);cb=zc.compress(counts.astype('<u2',copy=False).tobytes());tb,tdiag=encode_timing(posrows,gaprows,counts,mode,zc);first,repeat,sdiag=sign_alt_planes(vals,counts);s1=zc.compress(np.packbits(first,bitorder='little').tobytes());s2=zc.compress(np.packbits(repeat,bitorder='little').tobytes());ab=np.abs(vals);exc=ab!=1;eb=zc.compress(np.packbits(exc,bitorder='little').tobytes());mag=(ab[exc]-2).astype(np.int32);dc=dtype_code(mag);mb=zc.compress(mag.astype(DT[dc],copy=False).tobytes()) if mag.size else zc.compress(b'');oc=int(order[0]|(order[1]<<2)|(order[2]<<4));h=struct.pack(EHDR,EMAG,1,oc,mode,dc,*K.shape,len(cb),len(tb),len(s1),len(s2),len(eb),len(mb),0);parts={'counts':len(cb),'timing':len(tb),'sign_first':len(s1),'sign_repeat':len(s2),'exception_support':len(eb),'exception_magnitude':len(mb),'value_bytes':len(s1)+len(s2)+len(eb)+len(mb),'order':list(order),'level':level,**tdiag,**sdiag};return h+cb+tb+s1+s2+eb+mb,parts


def decode_main(blob):
    q=struct.unpack(EHDR,blob[:EHS]);magic,ver,oc,mode,dc,C,L,S,T,lc,lt,l1,l2,le,lm,lz=q
    if magic!=EMAG or ver!=1 or lz!=0:raise RuntimeError('event-rank header')
    p=EHS;cb=blob[p:p+lc];p+=lc;tb=blob[p:p+lt];p+=lt;s1=blob[p:p+l1];p+=l1;s2=blob[p:p+l2];p+=l2;eb=blob[p:p+le];p+=le;mb=blob[p:p+lm];p+=lm
    if p!=len(blob):raise RuntimeError('event-rank length')
    order=tuple((oc>>(2*i))&3 for i in range(3));shape=(C,L,S,T);psh=tuple(shape[i] for i in order)+(T,);ntr=int(np.prod(psh[:-1]));zd=zstd.ZstdDecompressor();counts=np.frombuffer(zd.decompress(cb),'<u2',count=ntr).astype(np.int32);ne=int(counts.sum());posrows=decode_timing(tb,counts,mode,zd)
    nn=int(np.count_nonzero(counts));first=np.unpackbits(np.frombuffer(zd.decompress(s1),np.uint8),bitorder='little',count=nn).astype(bool);repeat=np.unpackbits(np.frombuffer(zd.decompress(s2),np.uint8),bitorder='little',count=ne-nn).astype(bool);signs=np.empty(ne,bool);k=fk=rk=0
    for c0 in counts.tolist():
        c=int(c0)
        if not c:continue
        s=bool(first[fk]);fk+=1;signs[k]=s;k+=1
        for _ in range(1,c):
            if not repeat[rk]:s=not s
            rk+=1;signs[k]=s;k+=1
    if k!=ne:raise RuntimeError('rank sign accounting')
    exc=np.unpackbits(np.frombuffer(zd.decompress(eb),np.uint8),bitorder='little',count=ne).astype(bool);ab=np.ones(ne,np.int32)
    if exc.any():ab[exc]=np.frombuffer(zd.decompress(mb),dtype=DT[dc],count=int(exc.sum())).astype(np.int32)+2
    vals=np.where(signs,-ab,ab);tr=np.zeros((ntr,T),np.int32);k=0
    for i,pos in enumerate(posrows):
        c=pos.size
        if c:
            if pos[0]<0 or pos[-1]>=T or np.any(np.diff(pos)<=0):raise RuntimeError(('rank invalid positions',mode,i,pos[:5].tolist(),pos[-5:].tolist()))
            tr[i,pos]=vals[k:k+c];k+=c
    if k!=ne:raise RuntimeError('rank value accounting')
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
        for mode in range(7):
            for level in (19,22):
                b,parts=encode_main(K,order,mode,level);R=decode_main(b)
                if not np.array_equal(R,K):raise RuntimeError(('event-rank K decode',order,mode,level))
                rows.append((len(b),order,mode,level,b,parts))
    rows.sort(key=lambda x:x[0]);bm=rows[0];bo=best_out(O);topfmt='<8sdQQB';top=struct.pack(topfmt,b'ERTOP001',eps,len(bm[4]),len(bo[6]),0 if bo[1]=='gap' else 1)+bm[4]+bo[6];hs=struct.calcsize(topfmt);_,ee,lm,lo,ok=struct.unpack(topfmt,top[:hs]);RK=decode_main(top[hs:hs+lm]);obb=top[hs+lm:hs+lm+lo]
    if ok==0:
        A=decode(obb).reshape(O.shape);RO=undelta(A,1) if bo[2] else A
    else:
        A=decode_out_sparse(obb);RO=undelta(A,1) if bo[2] else A
    RG=undelta(RK,3);Y=np.empty_like(X)
    for tid,c,l,s in tm:Y[tid]=RG[c,l,s].astype(np.float32)*np.float32(2*ee)
    Y[outids]=RO.astype(np.float32)*np.float32(2*ee);me=float(np.max(np.abs(X-Y)));szb,sze=sz3_bytes(X,eps)
    names=['trace-gap-varint','rank-position-uint16','rank-position-delta-int16','rank-position-delta-zigzag','rank-gap-varint','rank-gap-delta-zigzag','rank-gap-delta-int16'];cands=[{'bytes':r[0],'order':list(r[1]),'timing_mode':names[r[2]],'level':r[3],'parts':r[5]} for r in rows[:30]];outmeta={'bytes':bo[0],'kind':bo[1],'tdiff':bo[2],'mode':bo[3],'level':bo[4],'perm':list(bo[5]) if bo[5] is not None else None,'parts':bo[7]}
    out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'eps':eps,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'main_best':cands[0],'main_candidates':cands,'outlier_best':outmeta,'container_bytes':len(top),'ratio':raw/len(top),'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'sz3':{'bytes':szb,'ratio':raw/szb,'maxerr':sze},'gain_vs_direct_sz3':szb/len(top),'strongest_verified_p75_baseline_bytes':133225,'gain_vs_strongest_verified_p75_baseline':133225/len(top),'two_x_gate_bytes':133225/2,'prior_record_bytes':70114}
    print(json.dumps(out,indent=2),flush=True);json.dump(out,open('soda_event_rank_surface.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
