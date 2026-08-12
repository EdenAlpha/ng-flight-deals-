import json,os,struct,sys
import numpy as np
import zstandard as zstd

# Reuse audited Soda geometry, PR #126 outlier codec, varints and sparse helpers.
src=open('research/soda_event_gap.py').read().split('\npath=sys.argv[1]')[0]
exec(compile(src,'soda_event_gap.py','exec'),globals())

# Same physical frame count/header footprint as PR #150: 6 timing frames +
# first-sign + repeat-sign + exception-support + exception-magnitude.
CMAG=b'RCTXv001'; CHDR='<8sBBBB4I10Q'; CHS=struct.calcsize(CHDR)


def trace_runs(pos):
    if not pos.size:return np.empty(0,np.int32),np.empty(0,np.int32)
    cut=np.r_[True,np.diff(pos)>1];starts=pos[cut];idx=np.flatnonzero(cut);ends=np.r_[idx[1:]-1,pos.size-1];lens=pos[ends]-starts+1
    return starts.astype(np.int32),lens.astype(np.int32)


def phase_labels(pos):
    out=np.empty(pos.size,np.uint8)
    if not pos.size:return out
    starts,lens=trace_runs(pos);k=0
    for ln0 in lens.tolist():
        ln=int(ln0)
        if ln==1:out[k]=0;k+=1
        else:
            out[k]=1
            if ln>2:out[k+1:k+ln-1]=2
            out[k+ln-1]=3;k+=ln
    if k!=pos.size:raise RuntimeError(('phase label count',k,pos.size))
    return out


def timing_ctx(comp,phase,runmode,mode,signs=None,for_value=False):
    comp=np.asarray(comp,np.int32);phase=np.asarray(phase,np.int32);runmode=np.asarray(runmode,np.int32)
    inside=(phase!=0).astype(np.int32)
    if mode==0:base=np.zeros(comp.size,np.int32)
    elif mode==1:base=phase
    elif mode==2:base=comp
    elif mode==3:base=comp*2+inside
    elif mode in (4,6):base=comp*4+phase
    elif mode==5:base=runmode*4+phase
    elif mode==7:base=comp*2+inside
    else:raise ValueError(mode)
    # Modes 6/7 add decoded sign only for exception and magnitude planes.
    if for_value and mode in (6,7):
        if signs is None:raise RuntimeError('sign context requested before sign decode')
        base=base*2+np.asarray(signs,bool).astype(np.int32)
    return base


def ctx_perm(ctx):
    ctx=np.asarray(ctx,np.int32)
    if not ctx.size:return np.empty(0,np.int64)
    return np.argsort(ctx,kind='stable')


def reorder_bits(bits,ctx):
    bits=np.asarray(bits,bool);p=ctx_perm(ctx);return bits[p],p

def restore_bits(sorted_bits,ctx):
    p=ctx_perm(ctx);out=np.empty(len(p),bool);out[p]=np.asarray(sorted_bits,bool);return out

def reorder_vals(vals,ctx):
    vals=np.asarray(vals);p=ctx_perm(ctx);return vals[p],p

def restore_vals(sorted_vals,ctx):
    p=ctx_perm(ctx);out=np.empty(len(p),np.asarray(sorted_vals).dtype);out[p]=sorted_vals;return out


def gather(K,order,threshold):
    P=np.transpose(K,order+(3,));sh=P.shape;tr=P.reshape(-1,sh[-1]);counts=np.count_nonzero(tr,axis=1).astype(np.uint16);modes=np.zeros(tr.shape[0],np.uint8);run_counts=[];rawg=[];startg=[];runlen=[];vals=[];comps=[];phases=[];rmodes=[];first_event=[];run_events=raw_events=0;all_runs=adjacent=0
    comp_axis=order.index(0);spatial_shape=sh[:-1]
    for i,row in enumerate(tr):
        pos=np.flatnonzero(row);c=pos.size
        if not c:continue
        coord=np.unravel_index(i,spatial_shape);comp=int(coord[comp_axis]);pl=phase_labels(pos);starts,lens=trace_runs(pos);nr=starts.size;all_runs+=nr;adjacent+=c-nr;use=(c>=2 and nr/c<=threshold);modes[i]=1 if use else 0
        vals.extend(row[pos].astype(np.int32).tolist());comps.extend([comp]*c);phases.extend(pl.tolist());rmodes.extend([int(use)]*c);fm=np.zeros(c,bool);fm[0]=True;first_event.extend(fm.tolist())
        if use:
            run_counts.append(nr);run_events+=c;prev_end=-1
            for st,ln in zip(starts.tolist(),lens.tolist()):startg.append(int(st)-prev_end);runlen.append(int(ln));prev_end=int(st)+int(ln)-1
        else:
            raw_events+=c;g=np.empty(c,np.int32);g[0]=pos[0]+1
            if c>1:g[1:]=np.diff(pos)
            rawg.extend(g.tolist())
    vals=np.asarray(vals,np.int32);comps=np.asarray(comps,np.uint8);phases=np.asarray(phases,np.uint8);rmodes=np.asarray(rmodes,np.uint8);first_event=np.asarray(first_event,bool)
    if vals.size!=int(counts.sum()) or vals.size!=comps.size or vals.size!=phases.size or vals.size!=first_event.size:raise RuntimeError('gather event metadata mismatch')
    diag={'all_runs':int(all_runs),'adjacent_events':int(adjacent),'adjacent_fraction':adjacent/max(1,int(counts.sum())),'run_mode_traces':int(modes.sum()),'raw_mode_traces':int(modes.size-modes.sum()),'run_mode_events':int(run_events),'raw_mode_events':int(raw_events),'threshold':threshold}
    return sh,counts,modes,np.asarray(run_counts,np.uint16),np.asarray(rawg,np.int32),np.asarray(startg,np.int32),np.asarray(runlen,np.int32),vals,comps,phases,rmodes,first_event,diag


def context_stats(ctx,bits=None):
    if not ctx.size:return {'contexts':0,'sizes':[]}
    u,c=np.unique(ctx,return_counts=True);out={'contexts':int(u.size),'sizes':[{'id':int(a),'n':int(b)} for a,b in zip(u,c)]}
    if bits is not None:
        bits=np.asarray(bits,bool);out['ones_by_context']=[{'id':int(a),'ones':int(bits[ctx==a].sum()),'n':int(np.sum(ctx==a))} for a in u]
    return out


def encode_main(K,order,threshold,level,ctxmode):
    zc=zstd.ZstdCompressor(level=level);sh,counts,modes,rc,rawg,startg,runlen,vals,comp,phase,rm,event_first,diag=gather(K,order,threshold);ne=vals.size;signs=vals<0
    # First sign stays trace-major. Repeat bits correspond to every event except the first event of each nonempty trace.
    first=signs[event_first];rep_mask=~event_first;prevsign=np.empty(ne,bool);k=0
    for c0 in counts.tolist():
        c=int(c0)
        if not c:continue
        prevsign[k]=signs[k]
        if c>1:prevsign[k+1:k+c]=signs[k:k+c-1]
        k+=c
    repeat=(signs==prevsign)[rep_mask];rctx=timing_ctx(comp[rep_mask],phase[rep_mask],rm[rep_mask],ctxmode);rsorted,_=reorder_bits(repeat,rctx)
    ab=np.abs(vals);exc=ab!=1;ectx=timing_ctx(comp,phase,rm,ctxmode,signs,True);esorted,_=reorder_bits(exc,ectx)
    mag=(ab[exc]-2).astype(np.int32);mctx=ectx[exc];msorted,_=reorder_vals(mag,mctx);dc=dtype_code(msorted)
    frames=[zc.compress(counts.astype('<u2',copy=False).tobytes()),zc.compress(np.packbits(modes,bitorder='little').tobytes()),zc.compress(rc.astype('<u2',copy=False).tobytes()),zc.compress(leb128_u(rawg)),zc.compress(leb128_u(startg)),zc.compress(leb128_u(runlen)),zc.compress(np.packbits(first,bitorder='little').tobytes()),zc.compress(np.packbits(rsorted,bitorder='little').tobytes()),zc.compress(np.packbits(esorted,bitorder='little').tobytes()),zc.compress(msorted.astype(DT[dc],copy=False).tobytes()) if msorted.size else zc.compress(b'')]
    oc=int(order[0]|(order[1]<<2)|(order[2]<<4));h=struct.pack(CHDR,CMAG,1,oc,dc,ctxmode,*K.shape,*[len(x) for x in frames]);parts={'counts':len(frames[0]),'modes':len(frames[1]),'run_counts':len(frames[2]),'raw_gaps':len(frames[3]),'run_start_gaps':len(frames[4]),'run_lengths':len(frames[5]),'sign_first':len(frames[6]),'sign_repeat':len(frames[7]),'exception_support':len(frames[8]),'exception_magnitude':len(frames[9]),'timing_bytes':sum(len(x) for x in frames[:6]),'value_bytes':sum(len(x) for x in frames[6:]),'ctxmode':ctxmode,'repeat_context':context_stats(rctx,repeat),'exception_context':context_stats(ectx,exc),'magnitude_context':context_stats(mctx),**diag,'level':level,'order':list(order)}
    return h+b''.join(frames),parts


def reconstruct_positions(counts,modes,rc,rawg,startg,runlen,T):
    posrows=[];kr=ks=0;jr=0
    for i,c0 in enumerate(counts.tolist()):
        c=int(c0)
        if not c:posrows.append(np.empty(0,np.int32));continue
        if not modes[i]:
            g=rawg[kr:kr+c];kr+=c;pos=(np.cumsum(g)-1).astype(np.int32)
        else:
            n=int(rc[jr]);jr+=1;pos=[];prev_end=-1
            for _ in range(n):
                st=prev_end+int(startg[ks]);ln=int(runlen[ks]);ks+=1
                if ln<=0:raise RuntimeError('bad context run len')
                pos.extend(range(st,st+ln));prev_end=st+ln-1
            pos=np.asarray(pos,np.int32)
            if pos.size!=c:raise RuntimeError(('context run event count',pos.size,c))
        if pos.size and (pos[0]<0 or pos[-1]>=T or np.any(np.diff(pos)<=0)):raise RuntimeError('context positions')
        posrows.append(pos)
    if kr!=rawg.size or ks!=int(rc.sum()) or jr!=int(modes.sum()):raise RuntimeError('context timing accounting')
    return posrows


def event_metadata_from_positions(posrows,order,psh,modes):
    comp_axis=order.index(0);comp=[];phase=[];rm=[];first=[]
    for i,pos in enumerate(posrows):
        c=pos.size
        if not c:continue
        coord=np.unravel_index(i,psh[:-1]);cc=int(coord[comp_axis]);pl=phase_labels(pos);comp.extend([cc]*c);phase.extend(pl.tolist());rm.extend([int(modes[i])]*c);fm=np.zeros(c,bool);fm[0]=True;first.extend(fm.tolist())
    return np.asarray(comp,np.uint8),np.asarray(phase,np.uint8),np.asarray(rm,np.uint8),np.asarray(first,bool)


def decode_main(blob):
    q=struct.unpack(CHDR,blob[:CHS]);magic,ver,oc,dc,ctxmode,C,L,S,T,*lens=q
    if magic!=CMAG or ver!=1 or ctxmode>7:raise RuntimeError('context header')
    p=CHS;fs=[]
    for n in lens:fs.append(blob[p:p+n]);p+=n
    if p!=len(blob):raise RuntimeError('context stream length')
    order=tuple((oc>>(2*i))&3 for i in range(3));shape=(C,L,S,T);psh=tuple(shape[i] for i in order)+(T,);ntr=int(np.prod(psh[:-1]));zd=zstd.ZstdDecompressor();counts=np.frombuffer(zd.decompress(fs[0]),'<u2',count=ntr).astype(np.int32);modes=np.unpackbits(np.frombuffer(zd.decompress(fs[1]),np.uint8),bitorder='little',count=ntr).astype(bool);nruntr=int(modes.sum());rc=np.frombuffer(zd.decompress(fs[2]),'<u2',count=nruntr).astype(np.int32);nraw=int(counts[~modes].sum());rawg=leb128_decode(zd.decompress(fs[3]),nraw);nr=int(rc.sum());startg=leb128_decode(zd.decompress(fs[4]),nr);runlen=leb128_decode(zd.decompress(fs[5]),nr);posrows=reconstruct_positions(counts,modes,rc,rawg,startg,runlen,T)
    comp,phase,rm,event_first=event_metadata_from_positions(posrows,order,psh,modes);ne=int(counts.sum());nn=int(np.count_nonzero(counts));first=np.unpackbits(np.frombuffer(zd.decompress(fs[6]),np.uint8),bitorder='little',count=nn).astype(bool);rep_mask=~event_first;rctx=timing_ctx(comp[rep_mask],phase[rep_mask],rm[rep_mask],ctxmode);rsort=np.unpackbits(np.frombuffer(zd.decompress(fs[7]),np.uint8),bitorder='little',count=ne-nn).astype(bool);repeat=restore_bits(rsort,rctx)
    signs=np.empty(ne,bool);k=fk=rk=0
    for c0 in counts.tolist():
        c=int(c0)
        if not c:continue
        s=bool(first[fk]);fk+=1;signs[k]=s;k+=1
        for _ in range(1,c):
            if not repeat[rk]:s=not s
            rk+=1;signs[k]=s;k+=1
    if k!=ne or fk!=nn or rk!=repeat.size:raise RuntimeError('context sign accounting')
    ectx=timing_ctx(comp,phase,rm,ctxmode,signs,True);esort=np.unpackbits(np.frombuffer(zd.decompress(fs[8]),np.uint8),bitorder='little',count=ne).astype(bool);exc=restore_bits(esort,ectx);nex=int(exc.sum());mctx=ectx[exc];msort=np.frombuffer(zd.decompress(fs[9]),dtype=DT[dc],count=nex).astype(np.int32) if nex else np.empty(0,np.int32);mag=restore_vals(msort,mctx) if nex else msort;ab=np.ones(ne,np.int32);ab[exc]=mag+2;vals=np.where(signs,-ab,ab);tr=np.zeros((ntr,T),np.int32);k=0
    for i,pos in enumerate(posrows):
        c=pos.size
        if c:tr[i,pos]=vals[k:k+c];k+=c
    if k!=ne:raise RuntimeError('context value accounting')
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
    # Freeze the exact PR #150 timing winner. Search only deterministic value contexts.
    order=(0,1,2);threshold=.6;level=22
    X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());eps=.1*std;step=2*eps;raw=X.nbytes;G,tm,outids,geom=geometry_map(X,gx,gy)
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    O=np.rint(X[outids]/step).astype(np.int32);K=delta(G,3);rows=[]
    for ctxmode in range(8):
        b,parts=encode_main(K,order,threshold,level,ctxmode);R=decode_main(b)
        if not np.array_equal(R,K):raise RuntimeError(('run-aware context K decode',ctxmode))
        rows.append((len(b),ctxmode,b,parts))
    rows.sort(key=lambda x:x[0]);bm=rows[0];bo=best_out(O);topfmt='<8sdQQB';top=struct.pack(topfmt,b'RCTOP001',eps,len(bm[2]),len(bo[6]),0 if bo[1]=='gap' else 1)+bm[2]+bo[6];hs=struct.calcsize(topfmt);_,ee,lm,lo,ok=struct.unpack(topfmt,top[:hs]);RK=decode_main(top[hs:hs+lm]);obb=top[hs+lm:hs+lm+lo]
    if ok==0:
        A=decode(obb).reshape(O.shape);RO=undelta(A,1) if bo[2] else A
    else:
        A=decode_out_sparse(obb);RO=undelta(A,1) if bo[2] else A
    RG=undelta(RK,3);Y=np.empty_like(X)
    for tid,c,l,s in tm:Y[tid]=RG[c,l,s].astype(np.float32)*np.float32(2*ee)
    Y[outids]=RO.astype(np.float32)*np.float32(2*ee);me=float(np.max(np.abs(X-Y)));szb,sze=sz3_bytes(X,eps)
    names=['none','run-phase','component','component-x-inside','component-x-run-phase','timingmode-x-run-phase','component-x-run-phase-plus-sign-for-values','component-x-inside-plus-sign-for-values'];cands=[{'main_bytes':r[0],'ctxmode':r[1],'context':names[r[1]],'parts':r[3]} for r in rows];outmeta={'bytes':bo[0],'kind':bo[1],'tdiff':bo[2],'mode':bo[3],'level':bo[4],'perm':list(bo[5]) if bo[5] is not None else None,'parts':bo[7]}
    out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'eps':eps,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'frozen_timing':{'order':list(order),'threshold':threshold,'level':level},'main_best':cands[0],'main_candidates':cands,'outlier_best':outmeta,'container_bytes':len(top),'ratio':raw/len(top),'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'sz3':{'bytes':szb,'ratio':raw/szb,'maxerr':sze},'gain_vs_direct_sz3':szb/len(top),'strongest_verified_p75_baseline_bytes':133225,'gain_vs_strongest_verified_p75_baseline':133225/len(top),'two_x_gate_bytes':133225/2,'prior_record_bytes':69677,'clears_two_x_gate':bool(len(top)<=133225/2)}
    print(json.dumps(out,indent=2),flush=True);json.dump(out,open('soda_run_aware_values.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
