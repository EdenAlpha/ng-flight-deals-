import json,struct,sys
import numpy as np

# Import PR #179.  This installs the verified exact trace-header transform into
# the PR #171 standalone base and also activates the compatibility guards for
# the older research codec namespaces.
import soda_record_header_transform as headerx
base=headerx.base

# Freeze PR #167's already-measured winner.  There is NO context search here.
REFINED_KIND=3  # singleton-by-relative-rank
RMAG=b'IGRFN001'
RHDR='<8sBBBB4I10B10Q'
RHS=struct.calcsize(RHDR)


def relative_bucket(j,n):
    # j is inter-run rank 1..n-1; n is already decoded from the run-count frame.
    return min(3,max(0,(4*j)//max(1,n)))


def refined_context(rc,lens,rcomp):
    # Exact PR #167 context kind 3.  Only the dominant singleton->singleton
    # class is split by relative run rank.  All labels are decoder-visible.
    out=[];k=0
    for n0 in np.asarray(rc).tolist():
        n=int(n0)
        if n:
            for j in range(1,n):
                a=int(lens[k+j-1]);b=int(lens[k+j]);lc=base.lenclass(a)*4+base.lenclass(b)
                rel=relative_bucket(j,n)
                c=rel if lc==0 else 4+lc-1
                out.append(c)
            k+=n
    if k!=len(lens):raise RuntimeError('refined context accounting')
    return np.asarray(out,np.int32)


def prepare_refined_raw(K,order=base.FROZEN_ORDER):
    sh,rc,startg,lens,rcomp,vals,phase,event_first,diag=base.gather_universal(K,order)
    nr=lens.size;ne=vals.size;rf=base.run_first_mask(rc);firstg=startg[rf];inter=(startg[~rf]-2).astype(np.int32)
    if np.any(inter<0):raise RuntimeError('inter invariant')
    firstcomp=rcomp[rf];long=lens>1;very=lens[long]>2
    f0=base.leb_u(rc);f1=base.first_payload(firstg,firstcomp,2)
    ctx=refined_context(rc,lens,rcomp);s,_=base.reorder_vals(inter,ctx);f2=base.leb_u(s)
    f3=np.packbits(long,bitorder='little').tobytes()
    f4=np.packbits(very,bitorder='little').tobytes() if long.any() else b''
    f5=base.leb_u(lens[long][very]-3) if very.any() else b''

    signs=vals<0;firstsign=signs[event_first];rep_mask=~event_first;prev=np.empty(ne,bool);k=0;j=0
    for n0 in rc.tolist():
        n=int(n0);c=int(lens[j:j+n].sum()) if n else 0;j+=n
        if c:
            prev[k]=signs[k]
            if c>1:prev[k+1:k+c]=signs[k:k+c-1]
            k+=c
    if k!=ne:raise RuntimeError('refined value accounting')
    repeat=(signs==prev)[rep_mask];rsort,_=base.reorder_bits(repeat,phase[rep_mask])
    ab=np.abs(vals);exc=ab!=1;esort,_=base.reorder_bits(exc,phase);mag=(ab[exc]-2).astype(np.int32);msort,_=base.reorder_vals(mag,phase[exc]);dc=base.dtype_code(msort)
    f6=np.packbits(firstsign,bitorder='little').tobytes();f7=np.packbits(rsort,bitorder='little').tobytes();f8=np.packbits(esort,bitorder='little').tobytes();f9=msort.astype(base.DT[dc],copy=False).tobytes()
    raw=[f0,f1,f2,f3,f4,f5,f6,f7,f8,f9]
    meta={'first_count':int(firstg.size),'inter_count':int(inter.size),'inter_zero_fraction':float(np.mean(inter==0)) if inter.size else 0.0,'context_kind':REFINED_KIND,'context_name':'singleton-by-relative-rank',**diag}
    return sh,dc,raw,meta


def encode_main_refined_fixed(K):
    sh,dc,raw,meta=prepare_refined_raw(K);frames=[];choices=[]
    # Keep PR #165/#179's exact frozen backend assignment.  The only changed
    # sample semantics are the zero-map ordering of the inter-run values.
    methods=base.FROZEN_METHODS
    for i,(r,m) in enumerate(zip(raw,methods)):
        b=base.comp_one(r,m)
        if base.decomp_one(b,m)!=r:raise RuntimeError(('refined backend roundtrip',i,m))
        frames.append(b);choices.append({'frame':i,'raw_bytes':len(r),'method':base.METHOD_NAMES[m],'bytes':len(b)})
    oc=int(base.FROZEN_ORDER[0]|(base.FROZEN_ORDER[1]<<2)|(base.FROZEN_ORDER[2]<<4))
    h=struct.pack(RHDR,RMAG,1,oc,dc,REFINED_KIND,*K.shape,*methods,*[len(x) for x in frames])
    names=['run_counts','first_starts','inter_starts','long_support','very_support','long_residual','sign_first','sign_repeat','exception_support','exception_magnitude']
    parts={names[i]:len(frames[i]) for i in range(10)};parts['timing_bytes']=sum(len(x) for x in frames[:6]);parts['value_bytes']=sum(len(x) for x in frames[6:]);parts['header_bytes']=RHS;parts['backend_choices']=choices;parts.update(meta)
    return h+b''.join(frames),parts


def decode_main_refined(blob):
    if len(blob)<RHS:raise RuntimeError('short refined main')
    q=struct.unpack(RHDR,blob[:RHS]);magic,ver,oc,dc,kind,C,L,S,T,*rest=q
    if magic!=RMAG or ver!=1 or kind!=REFINED_KIND:raise RuntimeError('refined header')
    methods=rest[:10];lf=rest[10:];p=RHS;frames=[]
    for n in lf:frames.append(blob[p:p+n]);p+=n
    if p!=len(blob):raise RuntimeError('refined stream length')
    raw=[base.decomp_one(frames[i],methods[i]) for i in range(10)]
    order=tuple((oc>>(2*i))&3 for i in range(3));shape=(C,L,S,T);psh=tuple(shape[i] for i in order)+(T,);ntr=int(np.prod(psh[:-1]))
    rc=base.leb_dec(raw[0],ntr);nr=int(rc.sum());rf=base.run_first_mask(rc);nn=int(np.count_nonzero(rc));firstcomp=base.first_components(rc,order,psh);firstg=base.first_restore(raw[1],nn,firstcomp,2)
    long=np.unpackbits(np.frombuffer(raw[3],np.uint8),bitorder='little',count=nr).astype(bool);nl=int(long.sum());very=np.unpackbits(np.frombuffer(raw[4],np.uint8),bitorder='little',count=nl).astype(bool) if nl else np.empty(0,bool);res=base.leb_dec(raw[5],int(very.sum())) if very.any() else np.empty(0,np.int32)
    runlens=np.ones(nr,np.int32);li=np.flatnonzero(long);runlens[li]=2
    if very.any():runlens[li[very]]=res+3
    rcomp=base.run_components(rc,order,psh);ctx=refined_context(rc,runlens,rcomp);ss=base.leb_dec(raw[2],nr-nn);inter=base.restore_vals(ss,ctx).astype(np.int32);startg=np.empty(nr,np.int32);startg[rf]=firstg;startg[~rf]=inter+2
    rows=base.reconstruct_positions(rc,startg,runlens,T);counts,phase,event_first=base.metadata_from_positions(rows);ne=int(counts.sum())
    firstsign=np.unpackbits(np.frombuffer(raw[6],np.uint8),bitorder='little',count=nn).astype(bool);rep_mask=~event_first;rsort=np.unpackbits(np.frombuffer(raw[7],np.uint8),bitorder='little',count=ne-nn).astype(bool);repeat=base.restore_bits(rsort,phase[rep_mask]);signs=np.empty(ne,bool);k=fk=rk=0
    for c0 in counts.tolist():
        c=int(c0)
        if not c:continue
        sg=bool(firstsign[fk]);fk+=1;signs[k]=sg;k+=1
        for _ in range(1,c):
            if not repeat[rk]:sg=not sg
            rk+=1;signs[k]=sg;k+=1
    if k!=ne or fk!=nn or rk!=repeat.size:raise RuntimeError('refined sign accounting')
    esort=np.unpackbits(np.frombuffer(raw[8],np.uint8),bitorder='little',count=ne).astype(bool);exc=base.restore_bits(esort,phase);nex=int(exc.sum());msort=np.frombuffer(raw[9],dtype=base.DT[dc],count=nex).astype(np.int32) if nex else np.empty(0,np.int32);mag=base.restore_vals(msort,phase[exc]) if nex else msort;ab=np.ones(ne,np.int32);ab[exc]=mag+2;vals=np.where(signs,-ab,ab);tr=np.zeros((ntr,T),np.int32);k=0
    for i,pos in enumerate(rows):
        c=pos.size
        if c:tr[i,pos]=vals[k:k+c];k+=c
    if k!=ne:raise RuntimeError('refined value accounting')
    P=tr.reshape(psh);inv=np.argsort(order);return np.transpose(P,tuple(inv)+(3,))


def encode_samples_refined(X,gx,gy,internal_eps):
    step=2*internal_eps;G,tm,outids,geom=base.geometry_map(X,gx,gy)
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    O=np.rint(X[outids]/step).astype(np.int32);K=base.delta(G,3);mb,parts=encode_main_refined_fixed(K);RK=decode_main_refined(mb)
    if not np.array_equal(RK,K):raise RuntimeError('refined K encode audit')
    bo=base.best_out(O);obb=bo[6];out_kind=0 if bo[1]=='gap' else 1;tdiff=1 if bo[2] else 0
    if out_kind==0:A=base.decode(obb).reshape(O.shape);RO=base.undelta(A,1) if tdiff else A
    else:A=base.decode_out_sparse(obb);RO=base.undelta(A,1) if tdiff else A
    if not np.array_equal(RO,O):raise RuntimeError('refined outlier audit')
    h=struct.pack(base.SAMP_HDR,base.SAMP_MAGIC,float(internal_eps),out_kind,tdiff,len(mb),len(obb))
    diag={'main_bytes':len(mb),'outlier_bytes':len(obb),'sample_header_bytes':base.SHS,'main_parts':parts,'outlier_kind':bo[1],'outlier_tdiff':bool(bo[2]),'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'refined_context_kind':REFINED_KIND,'refined_context_name':'singleton-by-relative-rank','frozen_backend_methods':[base.METHOD_NAMES[m] for m in base.FROZEN_METHODS]}
    return h+mb+obb,diag


def decode_samples_refined(blob,ntr,ns,gx,gy):
    if len(blob)<base.SHS:raise RuntimeError('short refined sample blob')
    magic,eps,ok,td,lm,lo=struct.unpack(base.SAMP_HDR,blob[:base.SHS])
    if magic!=base.SAMP_MAGIC:raise RuntimeError('bad refined sample magic')
    p=base.SHS;mb=blob[p:p+lm];p+=lm;obb=blob[p:p+lo];p+=lo
    if p!=len(blob):raise RuntimeError('refined sample blob length')
    RK=decode_main_refined(mb);RG=base.undelta(RK,3);dummy=np.empty((ntr,ns),np.float32);_,tm,outids,geom=base.geometry_map(dummy,gx,gy);Oshape=(len(outids),ns)
    if ok==0:A=base.decode(obb).reshape(Oshape);RO=base.undelta(A,1) if td else A
    elif ok==1:A=base.decode_out_sparse(obb);RO=base.undelta(A,1) if td else A
    else:raise RuntimeError('bad refined outlier kind')
    Y=np.empty((ntr,ns),np.float32)
    for tid,c,l,s in tm:Y[tid]=RG[c,l,s].astype(np.float32)*np.float32(2*eps)
    Y[outids]=RO.astype(np.float32)*np.float32(2*eps)
    return Y,float(eps),geom


# Compose the two independent improvements: PR #179 exact header transform and
# PR #167 zero-map inter-run context.  All outer container and IBM-float logic
# remains the already-verified PR #171 implementation.
base.encode_samples=encode_samples_refined
base.decode_samples=decode_samples_refined

if __name__=='__main__':
    if len(sys.argv)!=4:raise SystemExit('input.sgy output.srseg reconstructed.sgy')
    base.main(sys.argv[1],sys.argv[2],sys.argv[3])
