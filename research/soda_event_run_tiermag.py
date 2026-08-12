import json,os,struct,sys
import numpy as np
import zstandard as zstd

# Reuse the exact PR #150 timing grammar, geometry, sign transform and outlier search.
src=open('research/soda_event_run_timing.py').read().split("\nif __name__=='__main__':")[0]
exec(compile(src,'soda_event_run_timing.py','exec'),globals())

TMAG=b'TMAGv001'; THDR='<8sBBBB4I12Q'; THS=struct.calcsize(THDR)


def encode_tier(K,order,threshold,level,tiermode):
    zc=zstd.ZstdCompressor(level=level);sh,counts,modes,rc,rawg,startg,runlen,vals,diag=gather(K,order,threshold);first,repeat,sdiag=sign_alt_planes(vals,counts);ab=np.abs(vals);exc=ab!=1;exab=ab[exc]
    if tiermode==1:
        t1=exab>2;t2=np.empty(0,bool);res=(exab[t1]-3).astype(np.int32)
    elif tiermode==2:
        t1=exab>2;gt=exab[t1];t2=gt>3;res=(gt[t2]-4).astype(np.int32)
    else:raise ValueError(tiermode)
    dc=dtype_code(res)
    frames=[
        zc.compress(counts.astype('<u2',copy=False).tobytes()),
        zc.compress(np.packbits(modes,bitorder='little').tobytes()),
        zc.compress(rc.astype('<u2',copy=False).tobytes()),
        zc.compress(leb128_u(rawg)),
        zc.compress(leb128_u(startg)),
        zc.compress(leb128_u(runlen)),
        zc.compress(np.packbits(first,bitorder='little').tobytes()),
        zc.compress(np.packbits(repeat,bitorder='little').tobytes()),
        zc.compress(np.packbits(exc,bitorder='little').tobytes()),
        zc.compress(np.packbits(t1,bitorder='little').tobytes()),
        zc.compress(np.packbits(t2,bitorder='little').tobytes()) if tiermode==2 else zc.compress(b''),
        zc.compress(res.astype(DT[dc],copy=False).tobytes()) if res.size else zc.compress(b'')]
    oc=int(order[0]|(order[1]<<2)|(order[2]<<4));h=struct.pack(THDR,TMAG,1,oc,tiermode,dc,*K.shape,*[len(x) for x in frames]);parts={'counts':len(frames[0]),'modes':len(frames[1]),'run_counts':len(frames[2]),'raw_gaps':len(frames[3]),'run_start_gaps':len(frames[4]),'run_lengths':len(frames[5]),'sign_first':len(frames[6]),'sign_repeat':len(frames[7]),'exception_support':len(frames[8]),'gt2_support':len(frames[9]),'gt3_support':len(frames[10]),'super_magnitude':len(frames[11]),'timing_bytes':sum(len(x) for x in frames[:6]),'sign_bytes':len(frames[6])+len(frames[7]),'magnitude_logic_bytes':len(frames[8])+len(frames[9])+len(frames[10])+len(frames[11]),'value_bytes':sum(len(x) for x in frames[6:]),'events':int(vals.size),'exceptions':int(exc.sum()),'abs2':int(np.sum(exab==2)),'abs3':int(np.sum(exab==3)),'gt3':int(np.sum(exab>3)),'residual_values':int(res.size),'tiermode':tiermode,'order':list(order),'level':level,**diag,**sdiag};return h+b''.join(frames),parts


def decode_tier(blob):
    q=struct.unpack(THDR,blob[:THS]);magic,ver,oc,tiermode,dc,C,L,S,T,*lens=q
    if magic!=TMAG or ver!=1 or tiermode not in (1,2):raise RuntimeError('tier header')
    p=THS;fs=[]
    for n in lens:fs.append(blob[p:p+n]);p+=n
    if p!=len(blob):raise RuntimeError('tier stream length')
    order=tuple((oc>>(2*i))&3 for i in range(3));shape=(C,L,S,T);psh=tuple(shape[i] for i in order)+(T,);ntr=int(np.prod(psh[:-1]));zd=zstd.ZstdDecompressor();counts=np.frombuffer(zd.decompress(fs[0]),'<u2',count=ntr).astype(np.int32);modes=np.unpackbits(np.frombuffer(zd.decompress(fs[1]),np.uint8),bitorder='little',count=ntr).astype(bool);nruntr=int(modes.sum());rc=np.frombuffer(zd.decompress(fs[2]),'<u2',count=nruntr).astype(np.int32);nraw=int(counts[~modes].sum());rawg=leb128_decode(zd.decompress(fs[3]),nraw);nr=int(rc.sum());startg=leb128_decode(zd.decompress(fs[4]),nr);runlen=leb128_decode(zd.decompress(fs[5]),nr)
    ne=int(counts.sum());nn=int(np.count_nonzero(counts));first=np.unpackbits(np.frombuffer(zd.decompress(fs[6]),np.uint8),bitorder='little',count=nn).astype(bool);repeat=np.unpackbits(np.frombuffer(zd.decompress(fs[7]),np.uint8),bitorder='little',count=ne-nn).astype(bool);signs=np.empty(ne,bool);k=fk=rk=0
    for c0 in counts.tolist():
        c=int(c0)
        if not c:continue
        s=bool(first[fk]);fk+=1;signs[k]=s;k+=1
        for _ in range(1,c):
            if not repeat[rk]:s=not s
            rk+=1;signs[k]=s;k+=1
    if k!=ne:raise RuntimeError('tier sign accounting')
    exc=np.unpackbits(np.frombuffer(zd.decompress(fs[8]),np.uint8),bitorder='little',count=ne).astype(bool);nex=int(exc.sum());t1=np.unpackbits(np.frombuffer(zd.decompress(fs[9]),np.uint8),bitorder='little',count=nex).astype(bool);exab=np.full(nex,2,np.int32)
    if tiermode==1:
        nrval=int(t1.sum());res=np.frombuffer(zd.decompress(fs[11]),dtype=DT[dc],count=nrval).astype(np.int32) if nrval else np.empty(0,np.int32);exab[t1]=res+3
    else:
        n2=int(t1.sum());t2=np.unpackbits(np.frombuffer(zd.decompress(fs[10]),np.uint8),bitorder='little',count=n2).astype(bool);gt=np.full(n2,3,np.int32);nrval=int(t2.sum());res=np.frombuffer(zd.decompress(fs[11]),dtype=DT[dc],count=nrval).astype(np.int32) if nrval else np.empty(0,np.int32);gt[t2]=res+4;exab[t1]=gt
    ab=np.ones(ne,np.int32);ab[exc]=exab;vals=np.where(signs,-ab,ab);tr=np.zeros((ntr,T),np.int32);kv=kr=ks=0;jr=0
    for i,c0 in enumerate(counts.tolist()):
        c=int(c0)
        if not c:continue
        if not modes[i]:
            g=rawg[kr:kr+c];kr+=c;pos=np.cumsum(g)-1
        else:
            n=int(rc[jr]);jr+=1;pos=[];prev_end=-1
            for j in range(n):
                st=prev_end+int(startg[ks]);ln=int(runlen[ks]);ks+=1
                if ln<=0:raise RuntimeError('bad tier run len')
                pos.extend(range(st,st+ln));prev_end=st+ln-1
            pos=np.asarray(pos,np.int32)
            if pos.size!=c:raise RuntimeError(('tier run event count',pos.size,c))
        if pos.size and (pos[0]<0 or pos[-1]>=T or np.any(np.diff(pos)<=0)):raise RuntimeError('tier positions')
        tr[i,pos]=vals[kv:kv+c];kv+=c
    if kv!=ne or kr!=rawg.size or ks!=nr or jr!=nruntr:raise RuntimeError('tier timing accounting')
    P=tr.reshape(psh);inv=np.argsort(order);return np.transpose(P,tuple(inv)+(3,))


def main2(path):
    # Freeze PR #150's winning timing configuration first; test only magnitude semantics.
    X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());eps=.1*std;step=2*eps;raw=X.nbytes;G,tm,outids,geom=geometry_map(X,gx,gy)
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    O=np.rint(X[outids]/step).astype(np.int32);K=delta(G,3);order=(0,1,2);threshold=.6;level=22;rows=[]
    for tiermode in (1,2):
        b,parts=encode_tier(K,order,threshold,level,tiermode);R=decode_tier(b)
        if not np.array_equal(R,K):raise RuntimeError(('tier K decode',tiermode))
        rows.append((len(b),tiermode,b,parts))
    rows.sort(key=lambda x:x[0]);bm=rows[0];bo=best_out(O);topfmt='<8sdQQB';top=struct.pack(topfmt,b'TMTOP001',eps,len(bm[2]),len(bo[6]),0 if bo[1]=='gap' else 1)+bm[2]+bo[6];hs=struct.calcsize(topfmt);_,ee,lm,lo,ok=struct.unpack(topfmt,top[:hs]);RK=decode_tier(top[hs:hs+lm]);obb=top[hs+lm:hs+lm+lo]
    if ok==0:
        A=decode(obb).reshape(O.shape);RO=undelta(A,1) if bo[2] else A
    else:
        A=decode_out_sparse(obb);RO=undelta(A,1) if bo[2] else A
    RG=undelta(RK,3);Y=np.empty_like(X)
    for tid,c,l,s in tm:Y[tid]=RG[c,l,s].astype(np.float32)*np.float32(2*ee)
    Y[outids]=RO.astype(np.float32)*np.float32(2*ee);me=float(np.max(np.abs(X-Y)));szb,sze=sz3_bytes(X,eps)
    cands=[{'bytes':r[0],'tiermode':r[1],'parts':r[3]} for r in rows];outmeta={'bytes':bo[0],'kind':bo[1],'tdiff':bo[2],'mode':bo[3],'level':bo[4],'perm':list(bo[5]) if bo[5] is not None else None,'parts':bo[7]}
    out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'eps':eps,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'frozen_timing':{'order':list(order),'threshold':threshold,'level':level},'main_best':cands[0],'main_candidates':cands,'outlier_best':outmeta,'container_bytes':len(top),'ratio':raw/len(top),'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'sz3':{'bytes':szb,'ratio':raw/szb,'maxerr':sze},'gain_vs_direct_sz3':szb/len(top),'strongest_verified_p75_baseline_bytes':133225,'gain_vs_strongest_verified_p75_baseline':133225/len(top),'two_x_gate_bytes':133225/2,'prior_record_bytes':69722,'clears_two_x_gate':bool(len(top)<=133225/2)}
    print(json.dumps(out,indent=2),flush=True);json.dump(out,open('soda_event_run_tiermag.json','w'),indent=2)

if __name__=='__main__':main2(sys.argv[1])
