import json,os,struct,sys
import numpy as np

# Reuse PR #161's exact backend menu and all audited codec machinery.
src=open('research/soda_intergap_backend_hybrid.py').read().split('\ndef main(path):')[0]
exec(compile(src,'soda_intergap_backend_hybrid.py','exec'),globals())

RMAG=b'IGRFN001'
RHDR='<8sBBBB4I10B10Q'
RHS=struct.calcsize(RHDR)


def context_name(kind):
    return {0:'baseline-lenpair',1:'singleton-by-runrank',2:'singleton-by-trace-runcount',3:'singleton-by-relative-rank',4:'lenpair-x-runrank',5:'lenpair-x-trace-runcount',6:'lenpair-x-relative-rank',7:'singleton-by-component',8:'singleton-by-runrank-x-tracecount',9:'singleton-by-component-x-runrank'}[kind]

def trace_count_bucket(n):
    return 0 if n<=4 else (1 if n<=8 else (2 if n<=16 else 3))

def relative_bucket(j,n):
    # j is the inter-gap rank 1..n-1. Decoder knows n exactly.
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
    if k!=len(lens):raise RuntimeError('refined context accounting')
    return np.asarray(out,np.int32)

def prepare_common(K,order=(0,1,2)):
    sh,rc,startg,lens,rcomp,vals,phase,event_first,diag=gather_universal(K,order);nr=lens.size;ne=vals.size;rf=run_first_mask(rc);firstg=startg[rf];inter=(startg[~rf]-2).astype(np.int32)
    if np.any(inter<0):raise RuntimeError('inter invariant')
    firstcomp=rcomp[rf];long=lens>1;very=lens[long]>2
    f0=leb_u(rc);f1=first_payload(firstg,firstcomp,2);f3=np.packbits(long,bitorder='little').tobytes();f4=np.packbits(very,bitorder='little').tobytes() if long.any() else b'';f5=leb_u(lens[long][very]-3) if very.any() else b''
    signs=vals<0;firstsign=signs[event_first];rep_mask=~event_first;prev=np.empty(ne,bool);k=0;j=0
    for n0 in rc.tolist():
        n=int(n0);c=int(lens[j:j+n].sum()) if n else 0;j+=n
        if c:
            prev[k]=signs[k]
            if c>1:prev[k+1:k+c]=signs[k:k+c-1]
            k+=c
    if k!=ne:raise RuntimeError('value trace accounting')
    repeat=(signs==prev)[rep_mask];rsort,_=reorder_bits(repeat,phase[rep_mask]);ab=np.abs(vals);exc=ab!=1;esort,_=reorder_bits(exc,phase);mag=(ab[exc]-2).astype(np.int32);msort,_=reorder_vals(mag,phase[exc]);dc=dtype_code(msort)
    f6=np.packbits(firstsign,bitorder='little').tobytes();f7=np.packbits(rsort,bitorder='little').tobytes();f8=np.packbits(esort,bitorder='little').tobytes();f9=msort.astype(DT[dc],copy=False).tobytes()
    raw=[f0,f1,None,f3,f4,f5,f6,f7,f8,f9];meta={'first_count':int(firstg.size),'inter_count':int(inter.size),'inter_zero_fraction':float(np.mean(inter==0)) if inter.size else 0.0,**diag}
    return sh,dc,raw,meta,rc,lens,rcomp,inter

def compress_common(raw):
    common={}
    for i,r in enumerate(raw):
        if i==2:continue
        best,allrows=best_comp(r);n,m,b=best;common[i]=(n,m,b,allrows,len(r))
    return common

def encode_kind(K,kind,order,cache,common):
    sh,dc,raw,meta,rc,lens,rcomp,inter=cache;ctx=refined_context(rc,lens,rcomp,kind);s,_=reorder_vals(inter,ctx);r2=leb_u(s);best2,all2=best_comp(r2);n2,m2,b2=best2
    methods=[];frames=[];choices=[]
    for i in range(10):
        if i==2:n,m,b,allrows,rawlen=n2,m2,b2,all2,len(r2)
        else:n,m,b,allrows,rawlen=common[i]
        methods.append(m);frames.append(b);choices.append({'frame':i,'raw_bytes':rawlen,'chosen':METHOD_NAMES[m],'bytes':n,'all':allrows})
    oc=int(order[0]|(order[1]<<2)|(order[2]<<4));h=struct.pack(RHDR,RMAG,1,oc,dc,int(kind),*K.shape,*methods,*[len(x) for x in frames]);names=['run_counts','first_starts','inter_starts','long_support','very_support','long_residual','sign_first','sign_repeat','exception_support','exception_magnitude'];parts={names[i]:len(frames[i]) for i in range(10)};parts['timing_bytes']=sum(len(x) for x in frames[:6]);parts['value_bytes']=sum(len(x) for x in frames[6:]);parts['header_bytes']=RHS;parts['backend_choices']=choices;parts['context_kind']=kind;parts['context_name']=context_name(kind);parts['context_stats']=context_diag(ctx,inter);parts.update(meta)
    return h+b''.join(frames),parts

def decode_kind(blob):
    q=struct.unpack(RHDR,blob[:RHS]);magic,ver,oc,dc,kind,C,L,S,T,*rest=q
    if magic!=RMAG or ver!=1:raise RuntimeError('refined header')
    methods=rest[:10];lf=rest[10:];p=RHS;frames=[]
    for n in lf:frames.append(blob[p:p+n]);p+=n
    if p!=len(blob):raise RuntimeError('refined stream length')
    raw=[decomp_one(frames[i],methods[i]) for i in range(10)];order=tuple((oc>>(2*i))&3 for i in range(3));shape=(C,L,S,T);psh=tuple(shape[i] for i in order)+(T,);ntr=int(np.prod(psh[:-1]));rc=leb_dec(raw[0],ntr);nr=int(rc.sum());rf=run_first_mask(rc);nn=int(np.count_nonzero(rc));firstcomp=first_components(rc,order,psh);firstg=first_restore(raw[1],nn,firstcomp,2)
    long=np.unpackbits(np.frombuffer(raw[3],np.uint8),bitorder='little',count=nr).astype(bool);nl=int(long.sum());very=np.unpackbits(np.frombuffer(raw[4],np.uint8),bitorder='little',count=nl).astype(bool) if nl else np.empty(0,bool);res=leb_dec(raw[5],int(very.sum())) if very.any() else np.empty(0,np.int32);runlens=np.ones(nr,np.int32);li=np.flatnonzero(long);runlens[li]=2
    if very.any():runlens[li[very]]=res+3
    rcomp=run_components(rc,order,psh);ctx=refined_context(rc,runlens,rcomp,int(kind));ss=leb_dec(raw[2],nr-nn);inter=restore_vals(ss,ctx).astype(np.int32);startg=np.empty(nr,np.int32);startg[rf]=firstg;startg[~rf]=inter+2;rows=reconstruct_positions(rc,startg,runlens,T);counts,phase,event_first=metadata_from_positions(rows);ne=int(counts.sum())
    firstsign=np.unpackbits(np.frombuffer(raw[6],np.uint8),bitorder='little',count=nn).astype(bool);rep_mask=~event_first;rsort=np.unpackbits(np.frombuffer(raw[7],np.uint8),bitorder='little',count=ne-nn).astype(bool);repeat=restore_bits(rsort,phase[rep_mask]);signs=np.empty(ne,bool);k=fk=rk=0
    for c0 in counts.tolist():
        c=int(c0)
        if not c:continue
        sg=bool(firstsign[fk]);fk+=1;signs[k]=sg;k+=1
        for _ in range(1,c):
            if not repeat[rk]:sg=not sg
            rk+=1;signs[k]=sg;k+=1
    if k!=ne or fk!=nn or rk!=repeat.size:raise RuntimeError('refined sign accounting')
    esort=np.unpackbits(np.frombuffer(raw[8],np.uint8),bitorder='little',count=ne).astype(bool);exc=restore_bits(esort,phase);nex=int(exc.sum());msort=np.frombuffer(raw[9],dtype=DT[dc],count=nex).astype(np.int32) if nex else np.empty(0,np.int32);mag=restore_vals(msort,phase[exc]) if nex else msort;ab=np.ones(ne,np.int32);ab[exc]=mag+2;vals=np.where(signs,-ab,ab);tr=np.zeros((ntr,T),np.int32);k=0
    for i,pos in enumerate(rows):
        c=pos.size
        if c:tr[i,pos]=vals[k:k+c];k+=c
    if k!=ne:raise RuntimeError('refined value accounting')
    P=tr.reshape(psh);inv=np.argsort(order);return np.transpose(P,tuple(inv)+(3,))

def main(path):
    order=(0,1,2);X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());eps=.1*std;step=2*eps;rawbytes=X.nbytes;G,tm,outids,geom=geometry_map(X,gx,gy)
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    O=np.rint(X[outids]/step).astype(np.int32);K=delta(G,3);cache=prepare_common(K,order);common=compress_common(cache[2]);rows=[]
    for kind in range(10):
        print('CONTEXT',kind,context_name(kind),flush=True);b,parts=encode_kind(K,kind,order,cache,common);R=decode_kind(b)
        if not np.array_equal(R,K):raise RuntimeError(('refined exact K',kind))
        rows.append({'kind':kind,'name':context_name(kind),'main_bytes':len(b),'parts':parts,'blob':b});print(json.dumps({'kind':kind,'name':context_name(kind),'main_bytes':len(b),'inter_bytes':parts['inter_starts'],'timing_bytes':parts['timing_bytes']},indent=2),flush=True)
    rows.sort(key=lambda x:x['main_bytes']);best=rows[0];RK=decode_kind(best['blob']);bo=best_out(O);RO=decode_out_best(bo,O.shape)
    if not np.array_equal(RO,O):raise RuntimeError('refined outlier decode')
    RG=undelta(RK,3);recon=np.empty_like(X)
    for tid,c,l,s in tm:recon[tid]=RG[c,l,s].astype(np.float32)*np.float32(step)
    recon[outids]=RO.astype(np.float32)*np.float32(step);me=float(np.max(np.abs(X-recon)));szb,sze=sz3_bytes(X,eps);container=TOPS+best['main_bytes']+int(bo[0]);baseline=133225
    out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':rawbytes,'eps':eps,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'best':{k:v for k,v in best.items() if k!='blob'},'candidates':[{k:v for k,v in r.items() if k!='blob'} for r in rows],'outlier_bytes':int(bo[0]),'top_header_bytes':TOPS,'container_bytes':container,'ratio':float(rawbytes/container),'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'sz3':{'bytes':int(szb),'ratio':float(rawbytes/szb),'maxerr':float(sze)},'gain_vs_direct_sz3':float(szb/container),'strongest_verified_p75_baseline_bytes':baseline,'gain_vs_strongest_verified_p75_baseline':float(baseline/container),'prior_pr161_bytes':63911,'improvement_vs_pr161_bytes':int(63911-container)}
    print(json.dumps({k:out[k] for k in ('container_bytes','ratio','gain_vs_direct_sz3','gain_vs_strongest_verified_p75_baseline','improvement_vs_pr161_bytes','maxerr','valid')},indent=2),flush=True);json.dump(out,open('soda_intergap_context_refine.json','w'),indent=2)

main(sys.argv[1])
