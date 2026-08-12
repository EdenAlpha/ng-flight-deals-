import json,os,struct,sys
import numpy as np
import zstandard as zstd

# Reuse the fully audited PR #154 loader, geometry, hybrid raw/run timing grammar,
# outlier codec and run-phase value semantics. This experiment changes ONLY
# the order in which already-existing timing symbols are presented to Zstd.
src=open('research/soda_run_aware_values.py').read().split('\ndef main(path):')[0]
exec(compile(src,'soda_run_aware_values.py','exec'),globals())

TMAG=b'TCTXv001'
THDR='<8sBBBBBB4I10Q'
THS=struct.calcsize(THDR)
TOP='<8sdQQB'
TOPS=struct.calcsize(TOP)


def rank_bucket(r):
    r=np.asarray(r,np.int32);o=np.empty(r.size,np.int32)
    o[r==0]=0;o[r==1]=1;o[(r>=2)&(r<=3)]=2;o[(r>=4)&(r<=7)]=3;o[r>=8]=4
    return o


def count_bucket(c):
    c=np.asarray(c,np.int32);o=np.empty(c.size,np.int32)
    o[c<=4]=0;o[(c>=5)&(c<=16)]=1;o[(c>=17)&(c<=64)]=2;o[c>=65]=3
    return o


def len_bucket(x):
    x=np.asarray(x,np.int32);o=np.empty(x.size,np.int32)
    o[x==1]=0;o[x==2]=1;o[x==3]=2;o[x>=4]=3
    return o


def timing_metadata(counts,modes,rc,runlen,order,psh):
    comp_axis=order.index(0);raw_comp=[];raw_rank=[];raw_count=[];raw_first=[];run_comp=[];run_rank=[]
    jr=kr=0
    for i,c0 in enumerate(counts.tolist()):
        c=int(c0);coord=np.unravel_index(i,psh[:-1]);cc=int(coord[comp_axis])
        if not c:continue
        if not modes[i]:
            raw_comp.extend([cc]*c);raw_rank.extend(range(c));raw_count.extend([c]*c);raw_first.extend([1]+[0]*(c-1))
        else:
            n=int(rc[jr]);jr+=1;run_comp.extend([cc]*n);run_rank.extend(range(n));kr+=n
    if jr!=int(modes.sum()) or kr!=len(runlen):raise RuntimeError(('timing metadata accounting',jr,int(modes.sum()),kr,len(runlen)))
    return (np.asarray(raw_comp,np.int32),np.asarray(raw_rank,np.int32),np.asarray(raw_count,np.int32),np.asarray(raw_first,np.int32),np.asarray(run_comp,np.int32),np.asarray(run_rank,np.int32))


def raw_context(meta,mode):
    comp,rnk,cnt,first,_,_=meta;rb=rank_bucket(rnk);cb=count_bucket(cnt)
    if mode==0:return np.zeros(comp.size,np.int32)
    if mode==1:return comp
    if mode==2:return first
    if mode==3:return comp*2+first
    if mode==4:return rb
    if mode==5:return comp*5+rb
    if mode==6:return cb
    if mode==7:return comp*4+cb
    if mode==8:return cb*5+rb
    if mode==9:return comp*20+cb*5+rb
    raise ValueError(mode)


def run_context(meta,runlen,mode):
    *_,comp,rnk=meta;rb=rank_bucket(rnk);lb=len_bucket(runlen)
    if mode==0:return np.zeros(comp.size,np.int32)
    if mode==1:return comp
    if mode==2:return rb
    if mode==3:return comp*5+rb
    if mode==4:return lb
    if mode==5:return comp*4+lb
    if mode==6:return rb*4+lb
    if mode==7:return comp*20+rb*4+lb
    raise ValueError(mode)


def encode_main_tctx(K,order,threshold,level,rawmode,startmode):
    zc=zstd.ZstdCompressor(level=level)
    sh,counts,modes,rc,rawg,startg,runlen,vals,comp,phase,rm,event_first,diag=gather(K,order,threshold)
    psh=tuple(K.shape[i] for i in order)+(K.shape[3],);meta=timing_metadata(counts,modes,rc,runlen,order,psh)
    rctx=raw_context(meta,rawmode);sctx=run_context(meta,runlen,startmode)
    if rctx.size!=rawg.size or sctx.size!=startg.size:raise RuntimeError(('timing context sizes',rctx.size,rawg.size,sctx.size,startg.size))
    rsort,_=reorder_vals(rawg,rctx);ssort,_=reorder_vals(startg,sctx)

    # Freeze PR #154's winning value context: run phase only (ctxmode=1).
    ne=vals.size;signs=vals<0;first=signs[event_first];rep_mask=~event_first;prevsign=np.empty(ne,bool);k=0
    for c0 in counts.tolist():
        c=int(c0)
        if not c:continue
        prevsign[k]=signs[k]
        if c>1:prevsign[k+1:k+c]=signs[k:k+c-1]
        k+=c
    repeat=(signs==prevsign)[rep_mask];vrctx=timing_ctx(comp[rep_mask],phase[rep_mask],rm[rep_mask],1);vrsort,_=reorder_bits(repeat,vrctx)
    ab=np.abs(vals);exc=ab!=1;ectx=timing_ctx(comp,phase,rm,1,signs,True);esort,_=reorder_bits(exc,ectx);mag=(ab[exc]-2).astype(np.int32);mctx=ectx[exc];msort,_=reorder_vals(mag,mctx);dc=dtype_code(msort)
    frames=[zc.compress(counts.astype('<u2',copy=False).tobytes()),zc.compress(np.packbits(modes,bitorder='little').tobytes()),zc.compress(rc.astype('<u2',copy=False).tobytes()),zc.compress(leb128_u(rsort)),zc.compress(leb128_u(ssort)),zc.compress(leb128_u(runlen)),zc.compress(np.packbits(first,bitorder='little').tobytes()),zc.compress(np.packbits(vrsort,bitorder='little').tobytes()),zc.compress(np.packbits(esort,bitorder='little').tobytes()),zc.compress(msort.astype(DT[dc],copy=False).tobytes()) if msort.size else zc.compress(b'')]
    oc=int(order[0]|(order[1]<<2)|(order[2]<<4));h=struct.pack(THDR,TMAG,1,oc,dc,1,rawmode,startmode,*K.shape,*[len(x) for x in frames])
    parts={'counts':len(frames[0]),'modes':len(frames[1]),'run_counts':len(frames[2]),'raw_gaps':len(frames[3]),'run_start_gaps':len(frames[4]),'run_lengths':len(frames[5]),'sign_first':len(frames[6]),'sign_repeat':len(frames[7]),'exception_support':len(frames[8]),'exception_magnitude':len(frames[9]),'timing_bytes':sum(len(x) for x in frames[:6]),'value_bytes':sum(len(x) for x in frames[6:]),'raw_context':rawmode,'run_start_context':startmode,'raw_context_count':int(np.unique(rctx).size) if rctx.size else 0,'run_context_count':int(np.unique(sctx).size) if sctx.size else 0,**diag,'level':level,'order':list(order)}
    return h+b''.join(frames),parts


def decode_main_tctx(blob):
    q=struct.unpack(THDR,blob[:THS]);magic,ver,oc,dc,valctx,rawmode,startmode,C,L,S,T,*lens=q
    if magic!=TMAG or ver!=1 or valctx!=1 or rawmode>9 or startmode>7:raise RuntimeError('timing-context header')
    p=THS;fs=[]
    for n in lens:fs.append(blob[p:p+n]);p+=n
    if p!=len(blob):raise RuntimeError('timing-context stream length')
    order=tuple((oc>>(2*i))&3 for i in range(3));shape=(C,L,S,T);psh=tuple(shape[i] for i in order)+(T,);ntr=int(np.prod(psh[:-1]));zd=zstd.ZstdDecompressor()
    counts=np.frombuffer(zd.decompress(fs[0]),'<u2',count=ntr).astype(np.int32);modes=np.unpackbits(np.frombuffer(zd.decompress(fs[1]),np.uint8),bitorder='little',count=ntr).astype(bool);nruntr=int(modes.sum());rc=np.frombuffer(zd.decompress(fs[2]),'<u2',count=nruntr).astype(np.int32);nr=int(rc.sum());runlen=leb128_decode(zd.decompress(fs[5]),nr)
    meta=timing_metadata(counts,modes,rc,runlen,order,psh);rctx=raw_context(meta,rawmode);sctx=run_context(meta,runlen,startmode);nraw=int(counts[~modes].sum());rsort=leb128_decode(zd.decompress(fs[3]),nraw);ssort=leb128_decode(zd.decompress(fs[4]),nr);rawg=restore_vals(rsort,rctx).astype(np.int32);startg=restore_vals(ssort,sctx).astype(np.int32);posrows=reconstruct_positions(counts,modes,rc,rawg,startg,runlen,T)
    comp,phase,rm,event_first=event_metadata_from_positions(posrows,order,psh,modes);ne=int(counts.sum());nn=int(np.count_nonzero(counts));first=np.unpackbits(np.frombuffer(zd.decompress(fs[6]),np.uint8),bitorder='little',count=nn).astype(bool);rep_mask=~event_first;vrctx=timing_ctx(comp[rep_mask],phase[rep_mask],rm[rep_mask],1);vrsort=np.unpackbits(np.frombuffer(zd.decompress(fs[7]),np.uint8),bitorder='little',count=ne-nn).astype(bool);repeat=restore_bits(vrsort,vrctx)
    signs=np.empty(ne,bool);k=fk=rk=0
    for c0 in counts.tolist():
        c=int(c0)
        if not c:continue
        s=bool(first[fk]);fk+=1;signs[k]=s;k+=1
        for _ in range(1,c):
            if not repeat[rk]:s=not s
            rk+=1;signs[k]=s;k+=1
    if k!=ne or fk!=nn or rk!=repeat.size:raise RuntimeError('timing-context sign accounting')
    ectx=timing_ctx(comp,phase,rm,1,signs,True);esort=np.unpackbits(np.frombuffer(zd.decompress(fs[8]),np.uint8),bitorder='little',count=ne).astype(bool);exc=restore_bits(esort,ectx);nex=int(exc.sum());mctx=ectx[exc];msort=np.frombuffer(zd.decompress(fs[9]),dtype=DT[dc],count=nex).astype(np.int32) if nex else np.empty(0,np.int32);mag=restore_vals(msort,mctx) if nex else msort;ab=np.ones(ne,np.int32);ab[exc]=mag+2;vals=np.where(signs,-ab,ab);tr=np.zeros((ntr,T),np.int32);k=0
    for i,pos in enumerate(posrows):
        c=pos.size
        if c:tr[i,pos]=vals[k:k+c];k+=c
    if k!=ne:raise RuntimeError('timing-context value accounting')
    P=tr.reshape(psh);inv=np.argsort(order);return np.transpose(P,tuple(inv)+(3,))


def decode_out_best(bo,Oshape):
    if bo[1]=='gap':
        A=decode(bo[6]).reshape(Oshape);return undelta(A,1) if bo[2] else A
    A=decode_out_sparse(bo[6]);return undelta(A,1) if bo[2] else A


def main(path):
    order=(0,1,2);threshold=.6;level=22
    X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());eps=.1*std;step=2*eps;raw=X.nbytes;G,tm,outids,geom=geometry_map(X,gx,gy)
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    O=np.rint(X[outids]/step).astype(np.int32);K=delta(G,3);rows=[]
    for rawmode in range(10):
      for startmode in range(8):
        b,parts=encode_main_tctx(K,order,threshold,level,rawmode,startmode);R=decode_main_tctx(b)
        if not np.array_equal(R,K):raise RuntimeError(('timing-context K decode',rawmode,startmode))
        rows.append((len(b),rawmode,startmode,b,parts))
    rows.sort(key=lambda x:x[0]);bm=rows[0];bo=best_out(O);RO=decode_out_best(bo,O.shape)
    if not np.array_equal(RO,O):raise RuntimeError('timing-context outlier decode')
    top=struct.pack(TOP,b'TCTOP001',eps,len(bm[3]),len(bo[6]),0 if bo[1]=='gap' else 1)+bm[3]+bo[6];_,ee,lm,lo,ok=struct.unpack(TOP,top[:TOPS]);RK=decode_main_tctx(top[TOPS:TOPS+lm]);obb=top[TOPS+lm:TOPS+lm+lo]
    if ok==0:A=decode(obb).reshape(O.shape);RO=undelta(A,1) if bo[2] else A
    else:A=decode_out_sparse(obb);RO=undelta(A,1) if bo[2] else A
    RG=undelta(RK,3);Y=np.empty_like(X)
    for tid,c,l,s in tm:Y[tid]=RG[c,l,s].astype(np.float32)*np.float32(2*ee)
    Y[outids]=RO.astype(np.float32)*np.float32(2*ee);me=float(np.max(np.abs(X-Y)));szb,sze=sz3_bytes(X,eps);baseline=133225;gate=baseline/2
    rn=['none','component','first','component-x-first','rank-bucket','component-x-rank','count-bucket','component-x-count','count-x-rank','component-x-count-x-rank'];sn=['none','component','run-rank','component-x-run-rank','run-length','component-x-run-length','run-rank-x-length','component-x-run-rank-x-length']
    cands=[{'main_bytes':r[0],'rawmode':r[1],'raw_context':rn[r[1]],'startmode':r[2],'run_start_context':sn[r[2]],'parts':r[4]} for r in rows]
    out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'eps':eps,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'frozen_codec':{'order':list(order),'threshold':threshold,'level':level,'value_context':'run-phase'},'main_best':cands[0],'main_candidates':cands[:24],'outlier_best':{'bytes':int(bo[0]),'kind':bo[1],'tdiff':bool(bo[2]),'mode':int(bo[3]),'level':int(bo[4])},'container_bytes':len(top),'ratio':raw/len(top),'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'sz3':{'bytes':int(szb),'ratio':raw/szb,'maxerr':float(sze)},'gain_vs_direct_sz3':float(szb/len(top)),'strongest_verified_p75_baseline_bytes':baseline,'gain_vs_strongest_verified_p75_baseline':float(baseline/len(top)),'two_x_gate_bytes':gate,'prior_record_bytes':69006,'clears_two_x_gate':bool(len(top)<=gate)}
    print(json.dumps(out,indent=2),flush=True);json.dump(out,open('soda_timing_contexts.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
