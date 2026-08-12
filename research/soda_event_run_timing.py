import itertools,json,os,struct,sys
import numpy as np
import zstandard as zstd

# Reuse audited Soda geometry, PR #126 outlier codec, varints, sparse helpers.
src=open('research/soda_event_gap.py').read().split('\npath=sys.argv[1]')[0]
exec(compile(src,'soda_event_gap.py','exec'),globals())

RMAG=b'RUNEv001'; RHDR='<8sBBBB4I10Q'; RHS=struct.calcsize(RHDR)


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


def trace_runs(pos):
    if not pos.size:return np.empty(0,np.int32),np.empty(0,np.int32)
    cut=np.r_[True,np.diff(pos)>1];starts=pos[cut];idx=np.flatnonzero(cut);ends_idx=np.r_[idx[1:]-1,pos.size-1];lens=pos[ends_idx]-starts+1
    return starts.astype(np.int32),lens.astype(np.int32)


def gather(K,order,threshold):
    P=np.transpose(K,order+(3,));sh=P.shape;tr=P.reshape(-1,sh[-1]);counts=np.count_nonzero(tr,axis=1).astype(np.uint16);modes=np.zeros(tr.shape[0],np.uint8);run_counts=[];rawg=[];startg=[];runlen=[];vals=[];run_events=raw_events=0;all_runs=0;adjacent_events=0
    for i,row in enumerate(tr):
        pos=np.flatnonzero(row)
        c=pos.size
        if not c:continue
        vals.extend(row[pos].astype(np.int32).tolist());starts,lens=trace_runs(pos);nr=starts.size;all_runs+=nr;adjacent_events+=c-nr
        use=(c>=2 and nr/c<=threshold)
        if use:
            modes[i]=1;run_counts.append(nr);run_events+=c;prev_end=-1
            for st,ln in zip(starts.tolist(),lens.tolist()):
                startg.append(int(st)-prev_end);runlen.append(int(ln));prev_end=int(st)+int(ln)-1
        else:
            raw_events+=c;g=np.empty(c,np.int32);g[0]=pos[0]+1
            if c>1:g[1:]=np.diff(pos)
            rawg.extend(g.tolist())
    return sh,counts,modes,np.asarray(run_counts,np.uint16),np.asarray(rawg,np.int32),np.asarray(startg,np.int32),np.asarray(runlen,np.int32),np.asarray(vals,np.int32),{'all_runs':int(all_runs),'adjacent_events':int(adjacent_events),'adjacent_fraction':adjacent_events/max(1,int(counts.sum())),'run_mode_traces':int(modes.sum()),'raw_mode_traces':int(modes.size-modes.sum()),'run_mode_events':int(run_events),'raw_mode_events':int(raw_events),'threshold':threshold}


def encode_main(K,order,threshold,level):
    zc=zstd.ZstdCompressor(level=level);sh,counts,modes,rc,rawg,startg,runlen,vals,diag=gather(K,order,threshold);ab=np.abs(vals);exc=ab!=1;mag=(ab[exc]-2).astype(np.int32);dc=dtype_code(mag);first,repeat,sdiag=sign_alt_planes(vals,counts)
    frames=[zc.compress(counts.astype('<u2',copy=False).tobytes()),zc.compress(np.packbits(modes,bitorder='little').tobytes()),zc.compress(rc.astype('<u2',copy=False).tobytes()),zc.compress(leb128_u(rawg)),zc.compress(leb128_u(startg)),zc.compress(leb128_u(runlen)),zc.compress(np.packbits(first,bitorder='little').tobytes()),zc.compress(np.packbits(repeat,bitorder='little').tobytes()),zc.compress(np.packbits(exc,bitorder='little').tobytes()),zc.compress(mag.astype(DT[dc],copy=False).tobytes()) if mag.size else zc.compress(b'')]
    oc=int(order[0]|(order[1]<<2)|(order[2]<<4));h=struct.pack(RHDR,RMAG,1,oc,dc,0,*K.shape,*[len(x) for x in frames]);parts={'counts':len(frames[0]),'modes':len(frames[1]),'run_counts':len(frames[2]),'raw_gaps':len(frames[3]),'run_start_gaps':len(frames[4]),'run_lengths':len(frames[5]),'sign_first':len(frames[6]),'sign_repeat':len(frames[7]),'exception_support':len(frames[8]),'exception_magnitude':len(frames[9]),'timing_bytes':sum(len(x) for x in frames[:6]),'value_bytes':sum(len(x) for x in frames[6:]),'raw_gap_varint_bytes':len(leb128_u(rawg)),'run_start_varint_bytes':len(leb128_u(startg)),'run_length_varint_bytes':len(leb128_u(runlen)),**diag,**sdiag,'level':level,'order':list(order)};return h+b''.join(frames),parts


def decode_main(blob):
    q=struct.unpack(RHDR,blob[:RHS]);magic,ver,oc,dc,res,C,L,S,T,*lens=q
    if magic!=RMAG or ver!=1:raise RuntimeError('run header')
    p=RHS;fs=[]
    for n in lens:fs.append(blob[p:p+n]);p+=n
    if p!=len(blob):raise RuntimeError('run stream length')
    order=tuple((oc>>(2*i))&3 for i in range(3));shape=(C,L,S,T);psh=tuple(shape[i] for i in order)+(T,);ntr=int(np.prod(psh[:-1]));zd=zstd.ZstdDecompressor();counts=np.frombuffer(zd.decompress(fs[0]),'<u2',count=ntr).astype(np.int32);modes=np.unpackbits(np.frombuffer(zd.decompress(fs[1]),np.uint8),bitorder='little',count=ntr).astype(bool);nruntr=int(modes.sum());rc=np.frombuffer(zd.decompress(fs[2]),'<u2',count=nruntr).astype(np.int32);nraw=int(counts[~modes].sum());rawg=leb128_decode(zd.decompress(fs[3]),nraw);nr=int(rc.sum());startg=leb128_decode(zd.decompress(fs[4]),nr);runlen=leb128_decode(zd.decompress(fs[5]),nr)
    ne=int(counts.sum());nn=int(np.count_nonzero(counts));first=np.unpackbits(np.frombuffer(zd.decompress(fs[6]),np.uint8),bitorder='little',count=nn).astype(bool);repeat=np.unpackbits(np.frombuffer(zd.decompress(fs[7]),np.uint8),bitorder='little',count=ne-nn).astype(bool);signs=np.empty(ne,bool);k=fk=rk=0
    for c0 in counts.tolist():
        c=int(c0)
        if not c:continue
        s=bool(first[fk]);fk+=1;signs[k]=s;k+=1
        for _ in range(1,c):
            if not repeat[rk]:s=not s
            rk+=1;signs[k]=s;k+=1
    if k!=ne:raise RuntimeError('sign accounting')
    exc=np.unpackbits(np.frombuffer(zd.decompress(fs[8]),np.uint8),bitorder='little',count=ne).astype(bool);ab=np.ones(ne,np.int32)
    if exc.any():ab[exc]=np.frombuffer(zd.decompress(fs[9]),dtype=DT[dc],count=int(exc.sum())).astype(np.int32)+2
    vals=np.where(signs,-ab,ab);tr=np.zeros((ntr,T),np.int32);kv=kr=ks=0;jr=0
    for i,c0 in enumerate(counts.tolist()):
        c=int(c0)
        if not c:continue
        if not modes[i]:
            g=rawg[kr:kr+c];kr+=c;pos=np.cumsum(g)-1
        else:
            n=int(rc[jr]);jr+=1;pos=[];prev_end=-1
            for j in range(n):
                st=prev_end+int(startg[ks]);ln=int(runlen[ks]);ks+=1
                if ln<=0:raise RuntimeError('bad run len')
                pos.extend(range(st,st+ln));prev_end=st+ln-1
            pos=np.asarray(pos,np.int32)
            if pos.size!=c:raise RuntimeError(('run event count',pos.size,c))
        if pos.size and (pos[0]<0 or pos[-1]>=T or np.any(np.diff(pos)<=0)):raise RuntimeError('run positions')
        tr[i,pos]=vals[kv:kv+c];kv+=c
    if kv!=ne or kr!=rawg.size or ks!=nr or jr!=nruntr:raise RuntimeError(('run accounting',kv,ne,kr,rawg.size,ks,nr,jr,nruntr))
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
        for th in (.25,.4,.5,.6,.75,.9,1.0):
            for level in (19,22):
                b,parts=encode_main(K,order,th,level);R=decode_main(b)
                if not np.array_equal(R,K):raise RuntimeError(('run K decode',order,th,level))
                rows.append((len(b),order,th,level,b,parts))
    rows.sort(key=lambda x:x[0]);bm=rows[0];bo=best_out(O);topfmt='<8sdQQB';top=struct.pack(topfmt,b'RUTOP001',eps,len(bm[4]),len(bo[6]),0 if bo[1]=='gap' else 1)+bm[4]+bo[6];hs=struct.calcsize(topfmt);_,ee,lm,lo,ok=struct.unpack(topfmt,top[:hs]);RK=decode_main(top[hs:hs+lm]);obb=top[hs+lm:hs+lm+lo]
    if ok==0:
        A=decode(obb).reshape(O.shape);RO=undelta(A,1) if bo[2] else A
    else:
        A=decode_out_sparse(obb);RO=undelta(A,1) if bo[2] else A
    RG=undelta(RK,3);Y=np.empty_like(X)
    for tid,c,l,s in tm:Y[tid]=RG[c,l,s].astype(np.float32)*np.float32(2*ee)
    Y[outids]=RO.astype(np.float32)*np.float32(2*ee);me=float(np.max(np.abs(X-Y)));szb,sze=sz3_bytes(X,eps)
    cands=[{'bytes':r[0],'order':list(r[1]),'threshold':r[2],'level':r[3],'parts':r[5]} for r in rows[:30]];outmeta={'bytes':bo[0],'kind':bo[1],'tdiff':bo[2],'mode':bo[3],'level':bo[4],'perm':list(bo[5]) if bo[5] is not None else None,'parts':bo[7]}
    out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'eps':eps,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'main_best':cands[0],'main_candidates':cands,'outlier_best':outmeta,'container_bytes':len(top),'ratio':raw/len(top),'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'sz3':{'bytes':szb,'ratio':raw/szb,'maxerr':sze},'gain_vs_direct_sz3':szb/len(top),'strongest_verified_p75_baseline_bytes':133225,'gain_vs_strongest_verified_p75_baseline':133225/len(top),'two_x_gate_bytes':133225/2,'prior_record_bytes':70114}
    print(json.dumps(out,indent=2),flush=True);json.dump(out,open('soda_event_run_timing.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
