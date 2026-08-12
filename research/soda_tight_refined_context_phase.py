import json,os,struct,sys
import numpy as np

# Pull in PR #186's exact phase-map machinery plus PR #176's audited
# run/Rice grammar, backend menu, geometry and outlier codec without its CLI.
src=open('research/soda_tight_phase_rice.py').read().rsplit('\nmain(sys.argv[1],float(sys.argv[2]))',1)[0]
exec(compile(src,'soda_tight_phase_rice.py','exec'),globals())

RFMAG=b'TRCTX001'
RFHDR='<8sBBBBB4I10B10Q'
RFHS=struct.calcsize(RFHDR)


def context_name(kind):
    return {0:'lenpair',1:'singleton-runrank',2:'singleton-tracecount',3:'singleton-relative-rank',4:'lenpair-x-runrank',5:'lenpair-x-tracecount',6:'lenpair-x-relative-rank',7:'singleton-component',8:'singleton-runrank-x-tracecount',9:'singleton-component-x-runrank'}[kind]


def trace_count_bucket(n):
    return 0 if n<=4 else (1 if n<=8 else (2 if n<=16 else 3))


def relative_bucket(j,n):
    return min(3,max(0,(4*j)//max(1,n)))


def refined_context(rc,lens,rcomp,kind):
    out=[];k=0
    for n0 in np.asarray(rc).tolist():
        n=int(n0)
        if n:
            comp=int(rcomp[k]);tb=trace_count_bucket(n)
            for j in range(1,n):
                a=int(lens[k+j-1]);b=int(lens[k+j]);lc=lenclass(a)*4+lenclass(b);rb=0 if j==1 else (1 if j==2 else (2 if j<=4 else 3));rel=relative_bucket(j,n)
                if kind==0:c=lc
                elif kind==1:c=rb if lc==0 else 4+lc-1
                elif kind==2:c=tb if lc==0 else 4+lc-1
                elif kind==3:c=rel if lc==0 else 4+lc-1
                elif kind==4:c=lc*4+rb
                elif kind==5:c=lc*4+tb
                elif kind==6:c=lc*4+rel
                elif kind==7:c=comp if lc==0 else 3+lc-1
                elif kind==8:c=rb*4+tb if lc==0 else 16+lc-1
                elif kind==9:c=comp*4+rb if lc==0 else 12+lc-1
                else:raise ValueError(kind)
                out.append(c)
            k+=n
    if k!=len(lens):raise RuntimeError(('refined context accounting',k,len(lens)))
    return np.asarray(out,np.int32)


def nctx_for(ctx):
    return int(np.max(ctx))+1 if np.asarray(ctx).size else 1


def compress_exact(raw):
    best,allrows=best_comp(raw);n,m,b=best
    if decomp_one(b,m)!=raw:raise RuntimeError('refined backend roundtrip')
    return n,m,b,allrows


def prepare_refined_main(K):
    sh,dc,rawframes,meta=prepare_raw_frames(K,ORDER,CTXMODE)
    sh2,rc,startg,lens,rcomp,vals,phase,event_first,diag=gather_universal(K,ORDER)
    if tuple(sh2)!=tuple(sh):raise RuntimeError('refined shape disagreement')
    nr=lens.size;rf=run_first_mask(rc);inter=(startg[~rf]-2).astype(np.int32)
    if np.any(inter<0):raise RuntimeError('refined inter invariant')

    # Compress every frame that is independent of the inter-run context exactly once.
    chosen={};choices={}
    for i in (0,1,3,4,5,6,7,8):
        n,m,b,rows=compress_exact(rawframes[i]);chosen[i]=(n,m,b);choices[i]=rows

    # Magnitude plane: retain PR #176's exact raw-vs-contextual-Rice choice.
    ab=np.abs(vals);exc=ab!=1;mag=(ab[exc]-2).astype(np.int32);mctx=phase[exc].astype(np.int32)
    raw9=rawframes[9];rice9,d9=rice_encode_context(mag,mctx,4)
    magrows=[]
    for rep,rr in ((0,raw9),(1,rice9)):
        n,m,b,rows=compress_exact(rr);magrows.append((n,rep,m,b,rows,len(rr)))
    magrows.sort(key=lambda x:(x[0],x[1],x[2]));mwin=magrows[0];chosen[9]=(mwin[0],mwin[2],mwin[3]);choices[9]=mwin[4]

    # Search only decoder-known inter-run contexts. No context map is ever sent.
    irows=[]
    for kind in range(10):
        ctx=refined_context(rc,lens,rcomp,kind)
        if ctx.size!=inter.size:raise RuntimeError(('refined context size',kind,ctx.size,inter.size))
        s,_=reorder_vals(inter,ctx);raw=leb_u(s);n,m,b,backs=compress_exact(raw);irows.append((n,kind,0,m,b,backs,len(raw),nctx_for(ctx)))
        rice,rd=rice_encode_context(inter,ctx,nctx_for(ctx));n,m,b,backs=compress_exact(rice);irows.append((n,kind,1,m,b,backs,len(rice),nctx_for(ctx)))
    irows.sort(key=lambda x:(x[0],x[1],x[2],x[3]));iwin=irows[0];chosen[2]=(iwin[0],iwin[3],iwin[4]);choices[2]=iwin[5]

    code=int(iwin[2])|(int(mwin[1])<<1);kind=int(iwin[1]);methods=[chosen[i][1] for i in range(10)];frames=[chosen[i][2] for i in range(10)];oc=int(ORDER[0]|(ORDER[1]<<2)|(ORDER[2]<<4));h=struct.pack(RFHDR,RFMAG,1,oc,dc,code,kind,*K.shape,*methods,*[len(x) for x in frames])
    names=['run_counts','first_starts','inter_starts','long_support','very_support','long_residual','sign_first','sign_repeat','exception_support','exception_magnitude'];parts={names[i]:len(frames[i]) for i in range(10)}
    parts.update({'header_bytes':RFHS,'timing_bytes':sum(len(x) for x in frames[:6]),'value_bytes':sum(len(x) for x in frames[6:]),'context_kind':kind,'context_name':context_name(kind),'rep_inter_rice':bool(iwin[2]),'rep_magnitude_rice':bool(mwin[1]),'inter_context_count':int(iwin[7]),'inter_candidates':[{'bytes':int(r[0]),'context_kind':int(r[1]),'context_name':context_name(int(r[1])),'rice':bool(r[2]),'backend':METHOD_NAMES[int(r[3])],'pre_backend_bytes':int(r[6]),'contexts':int(r[7])} for r in irows],'magnitude_candidates':[{'bytes':int(r[0]),'rice':bool(r[1]),'backend':METHOD_NAMES[int(r[2])],'pre_backend_bytes':int(r[5])} for r in magrows],**meta})
    return h+b''.join(frames),parts


def decode_refined_main(blob):
    q=struct.unpack(RFHDR,blob[:RFHS]);magic,ver,oc,dc,code,kind,C,L,S,T,*rest=q
    if magic!=RFMAG or ver!=1 or kind>9:raise RuntimeError('refined main header')
    inter_rice=bool(code&1);mag_rice=bool(code&2);methods=rest[:10];lf=rest[10:];p=RFHS;frames=[]
    for n in lf:frames.append(blob[p:p+n]);p+=n
    if p!=len(blob):raise RuntimeError('refined main stream length')
    raw=[decomp_one(frames[i],methods[i]) for i in range(10)];order=tuple((oc>>(2*i))&3 for i in range(3));shape=(C,L,S,T);psh=tuple(shape[i] for i in order)+(T,);ntr=int(np.prod(psh[:-1]));rc=leb_dec(raw[0],ntr);nr=int(rc.sum());rf=run_first_mask(rc);nn=int(np.count_nonzero(rc));firstcomp=first_components(rc,order,psh);firstg=first_restore(raw[1],nn,firstcomp,2)
    long=np.unpackbits(np.frombuffer(raw[3],np.uint8),bitorder='little',count=nr).astype(bool);nl=int(long.sum());very=np.unpackbits(np.frombuffer(raw[4],np.uint8),bitorder='little',count=nl).astype(bool) if nl else np.empty(0,bool);res=leb_dec(raw[5],int(very.sum())) if very.any() else np.empty(0,np.int32);runlens=np.ones(nr,np.int32);li=np.flatnonzero(long);runlens[li]=2
    if very.any():runlens[li[very]]=res+3
    rcomp=run_components(rc,order,psh);ictx=refined_context(rc,runlens,rcomp,int(kind));ni=nr-nn
    if inter_rice:inter=rice_decode_context(raw[2],ictx,nctx_for(ictx))
    else:ss=leb_dec(raw[2],ni);inter=restore_vals(ss,ictx).astype(np.int32)
    startg=np.empty(nr,np.int32);startg[rf]=firstg;startg[~rf]=inter+2;rows=reconstruct_positions(rc,startg,runlens,T);counts,phase,event_first=metadata_from_positions(rows);ne=int(counts.sum())
    firstsign=np.unpackbits(np.frombuffer(raw[6],np.uint8),bitorder='little',count=nn).astype(bool);rep_mask=~event_first;rsort=np.unpackbits(np.frombuffer(raw[7],np.uint8),bitorder='little',count=ne-nn).astype(bool);repeat=restore_bits(rsort,phase[rep_mask]);signs=np.empty(ne,bool);k=fk=rk=0
    for c0 in counts.tolist():
        c=int(c0)
        if not c:continue
        s=bool(firstsign[fk]);fk+=1;signs[k]=s;k+=1
        for _ in range(1,c):
            if not repeat[rk]:s=not s
            rk+=1;signs[k]=s;k+=1
    if k!=ne or fk!=nn or rk!=repeat.size:raise RuntimeError('refined sign accounting')
    esort=np.unpackbits(np.frombuffer(raw[8],np.uint8),bitorder='little',count=ne).astype(bool);exc=restore_bits(esort,phase);nex=int(exc.sum());mctx=phase[exc].astype(np.int32)
    if mag_rice:mag=rice_decode_context(raw[9],mctx,4)
    else:msort=np.frombuffer(raw[9],dtype=DT[dc],count=nex).astype(np.int32) if nex else np.empty(0,np.int32);mag=restore_vals(msort,mctx) if nex else msort
    ab=np.ones(ne,np.int32);ab[exc]=mag+2;vals=np.where(signs,-ab,ab);tr=np.zeros((ntr,T),np.int32);k=0
    for i,pos in enumerate(rows):
        c=pos.size
        if c:tr[i,pos]=vals[k:k+c];k+=c
    if k!=ne:raise RuntimeError('refined value accounting')
    P=tr.reshape(psh);inv=np.argsort(order);return np.transpose(P,tuple(inv)+(3,))


def decode_out_exact(bo,Oshape):
    return decode_out_blob(bo[6],0 if bo[1]=='gap' else 1,1 if bo[2] else 0,Oshape)


def nearest_states(X,tm,outids,shape,step):
    G=np.zeros(shape,np.int32)
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid].astype(np.float64)/step).astype(np.int32)
    O=np.rint(X[outids].astype(np.float64)/step).astype(np.int32)
    return G,O


def eval_no_phase(X,tm,outids,shape,internal_eps):
    step=2*internal_eps;G,O=nearest_states(X,tm,outids,shape,step);K=delta(G,3);mb,parts=prepare_refined_main(K);RK=decode_refined_main(mb)
    if not np.array_equal(RK,K):raise RuntimeError('refined no-phase K')
    bo=best_out(O);RO=decode_out_exact(bo,O.shape)
    if not np.array_equal(RO,O):raise RuntimeError('refined no-phase outlier')
    ok=0 if bo[1]=='gap' else 1;td=1 if bo[2] else 0;top=struct.pack(TOP_HDR,TOP_MAGIC,float(internal_eps),ok,td,len(mb),len(bo[6]))+mb+bo[6]
    magic,ee,ook,tt,lm,lo=struct.unpack(TOP_HDR,top[:TOP_HS]);p=TOP_HS;DRK=decode_refined_main(top[p:p+lm]);p+=lm;DRO=decode_out_blob(top[p:p+lo],ook,tt,O.shape);p+=lo
    if magic!=TOP_MAGIC or p!=len(top) or not np.array_equal(DRK,K) or not np.array_equal(DRO,O):raise RuntimeError('refined no-phase top decode')
    RG=undelta(DRK,3);Y=np.empty_like(X)
    for tid,c,l,s in tm:Y[tid]=RG[c,l,s].astype(np.float32)*np.float32(2*ee)
    Y[outids]=DRO.astype(np.float32)*np.float32(2*ee)
    return {'container_bytes':len(top),'main_bytes':len(mb),'outlier_bytes':int(bo[0]),'main_parts':parts,'K_nonzero_fraction':float(np.mean(K!=0)),'recon':Y}


def decode_phase_top_refined(blob,main_shape,Oshape):
    q=struct.unpack(PHHDR,blob[:PHHS]);magic,eps,nph,pm,opm,ocode,lp,lop,lm,lo=q
    if magic!=PHMAG or nph!=NPH:raise RuntimeError('refined phase top header')
    p=PHHS;pb=blob[p:p+lp];p+=lp;opb=blob[p:p+lop];p+=lop;mb=blob[p:p+lm];p+=lm;obb=blob[p:p+lo];p+=lo
    if p!=len(blob):raise RuntimeError('refined phase top length')
    P=unpack_nibbles(decomp_one(pb,pm),int(np.prod(main_shape))).reshape(main_shape);OP=unpack_nibbles(decomp_one(opb,opm),Oshape[0]);RK=decode_refined_main(mb);RO=decode_out_blob(obb,ocode&1,(ocode>>1)&1,Oshape)
    return float(eps),P,OP,RK,RO


def eval_phase(X,tm,outids,shape,internal_eps):
    step=2*internal_eps;G,P,O,OP,pdiag=phase_quantize(X,tm,outids,shape,step);K=delta(G,3);mb,parts=prepare_refined_main(K);RK=decode_refined_main(mb)
    if not np.array_equal(RK,K):raise RuntimeError('refined phase K')
    bo=best_out(O);RO=decode_out_exact(bo,O.shape)
    if not np.array_equal(RO,O):raise RuntimeError('refined phase outlier')
    top,pacct=encode_phase_top(internal_eps,P,OP,mb,bo);ee,DP,DOP,DRK,DRO=decode_phase_top_refined(top,G.shape[:-1],O.shape)
    if not np.array_equal(DP,P) or not np.array_equal(DOP,OP) or not np.array_equal(DRK,K) or not np.array_equal(DRO,O):raise RuntimeError('refined phase exact top decode')
    RG=undelta(DRK,3);Y=reconstruct(X.shape,tm,outids,RG,DRO,DP,DOP,2*ee)
    return {'container_bytes':len(top),'main_bytes':len(mb),'outlier_bytes':int(bo[0]),'main_parts':parts,'phase_accounting':pacct,'phase_diag':pdiag,'K_nonzero_fraction':float(np.mean(K!=0)),'recon':Y}


def old_phase_bytes(X,tm,outids,shape,internal_eps):
    step=2*internal_eps;G,P,O,OP,pdiag=phase_quantize(X,tm,outids,shape,step);K=delta(G,3);bm,_=choose_main(K);bo=best_out(O);top,_=encode_phase_top(internal_eps,P,OP,bm[3],bo);return len(top)


def main(path,frac):
    X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());public_eps=float(frac)*std;internal_eps=public_eps*INTERNAL_SAFETY;raw=int(X.nbytes);G0,tm,outids,geom=geometry_map(X,gx,gy)
    incumbent=baseline_current(X,tm,outids,G0.shape,public_eps,internal_eps);oldphase=old_phase_bytes(X,tm,outids,G0.shape,internal_eps);npres=eval_no_phase(X,tm,outids,G0.shape,internal_eps);phres=eval_phase(X,tm,outids,G0.shape,internal_eps)
    for r in (npres,phres):
        r['maxerr']=float(np.max(np.abs(X-r.pop('recon'))));r['valid']=bool(r['maxerr']<=public_eps*(1+3e-6))
        if not r['valid']:raise RuntimeError(('refined hard error',r['maxerr'],public_eps))
    winner=min([('refined_no_phase',npres),('refined_phase',phres)],key=lambda x:x[1]['container_bytes']);szb,sze=sz3_bytes(X,public_eps);best=winner[1]
    out={'file':os.path.basename(path),'shape':list(X.shape),'epsilon_fraction_of_std':float(frac),'public_eps':public_eps,'internal_eps':internal_eps,'raw_bytes':raw,'geometry':geom,'old_context_incumbent_bytes':int(incumbent['container_bytes']),'old_phase_bytes':int(oldphase),'refined_no_phase':npres,'refined_phase':phres,'winner':winner[0],'winner_bytes':int(best['container_bytes']),'improvement_vs_old_best_bytes':int(min(incumbent['container_bytes'],oldphase)-best['container_bytes']),'improvement_vs_old_best_percent':float(100*(min(incumbent['container_bytes'],oldphase)-best['container_bytes'])/min(incumbent['container_bytes'],oldphase)),'sz3':{'bytes':int(szb),'ratio':float(raw/szb),'maxerr':float(sze)},'gain_vs_direct_sz3':float(szb/best['container_bytes'])}
    print(json.dumps({'frac':frac,'old_no_phase':incumbent['container_bytes'],'old_phase':oldphase,'refined_no_phase':npres['container_bytes'],'refined_phase':phres['container_bytes'],'winner':out['winner'],'winner_bytes':out['winner_bytes'],'improvement_bytes':out['improvement_vs_old_best_bytes'],'gain_sz3':out['gain_vs_direct_sz3'],'np_context':npres['main_parts']['context_name'],'ph_context':phres['main_parts']['context_name']},indent=2),flush=True);json.dump(out,open('soda_tight_refined_context_phase.json','w'),indent=2)

main(sys.argv[1],float(sys.argv[2]))
