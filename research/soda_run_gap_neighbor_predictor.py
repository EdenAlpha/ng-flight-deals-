import json,os,struct,sys
import numpy as np

# Reuse PR #161's verified structural representation, frame backend chooser,
# geometry, value coding, outlier codec, and fidelity checks. This experiment
# changes only the 71,547-symbol inter-run gap-minus-2 sequence.
src=open('research/soda_intergap_backend_hybrid.py').read().split('\ndef main(path):')[0]
exec(compile(src,'soda_intergap_backend_hybrid.py','exec'),globals())

NMAG=b'NGPRED01'
NHDR='<8sBBBBB4I11B11Q'
NHS=struct.calcsize(NHDR)
COMP_CACHE={}


def cached_best(raw):
    key=raw
    if key not in COMP_CACHE:COMP_CACHE[key]=best_comp(raw)
    return COMP_CACHE[key]


def zz_enc(a):
    a=np.asarray(a,np.int64);return np.where(a>=0,2*a,-2*a-1).astype(np.int32)

def zz_dec(z):
    z=np.asarray(z,np.int64);return np.where((z&1)!=0,-((z>>1)+1),z>>1).astype(np.int32)


def rank_warp(prev,m):
    prev=np.asarray(prev,np.int32);mp=prev.size
    if m<=0:return np.empty(0,np.int32)
    if mp<=0:return np.zeros(m,np.int32)
    if m==1:return np.asarray([int(prev[(mp-1)//2])],np.int32)
    if mp==1:return np.full(m,int(prev[0]),np.int32)
    out=np.empty(m,np.int32);den=m-1
    for j in range(m):
        num=j*(mp-1);lo=num//den;rem=num-lo*den;hi=min(lo+1,mp-1)
        out[j]=int((int(prev[lo])*(den-rem)+int(prev[hi])*rem+den//2)//den)
    return out


def neighbor_seq(seqs,i,physical_axis,order,spatial_shape):
    pos=order.index(physical_axis);coord=list(np.unravel_index(i,spatial_shape))
    if coord[pos]<=0:return None
    coord[pos]-=1;j=int(np.ravel_multi_index(tuple(coord),spatial_shape))
    if j>=i:raise RuntimeError(('noncausal neighbor',i,j,physical_axis,order))
    return seqs[j]


def predictor_for_mode(seqs,i,m,mode,order,spatial_shape):
    if mode==0:return np.zeros(m,np.int32)
    axes={1:(2,),2:(1,),3:(0,),4:(2,1),5:(2,1,0)}[mode];preds=[]
    for ax in axes:
        q=neighbor_seq(seqs,i,ax,order,spatial_shape)
        if q is not None and len(q):preds.append(rank_warp(q,m))
    if not preds:return np.zeros(m,np.int32)
    if len(preds)==1:return preds[0]
    A=np.stack(preds).astype(np.int64);return np.rint(A.mean(axis=0)).astype(np.int32)


def split_inter(rc,inter):
    mc=np.maximum(np.asarray(rc,np.int32)-1,0);off=np.r_[0,np.cumsum(mc,dtype=np.int64)];rows=[np.asarray(inter[off[i]:off[i+1]],np.int32) for i in range(len(mc))]
    if int(off[-1])!=len(inter):raise RuntimeError('inter split accounting')
    return mc,rows


def choose_adaptive_modes(rows,order,spatial_shape,criterion):
    modes=[];seqs=[]
    for i,x in enumerate(rows):
        m=len(x)
        if not m:seqs.append(x);continue
        best=None
        for mode in range(6):
            p=predictor_for_mode(seqs,i,m,mode,order,spatial_shape);r=x-p;z=zz_enc(r)
            if criterion==0:score=(len(leb_u(z)),int(np.count_nonzero(r)),int(np.abs(r.astype(np.int64)).sum()),mode)
            else:score=(int(np.count_nonzero(r)),int(np.abs(r.astype(np.int64)).sum()),len(leb_u(z)),mode)
            if best is None or score<best[0]:best=(score,mode)
        modes.append(best[1]);seqs.append(x)
    return np.asarray(modes,np.uint8)


def transform_inter(rc,inter,order,spatial_shape,predcode,style):
    mc,rows=split_inter(rc,inter);seqs=[];res=[];active_modes=[]
    adaptive=predcode in (6,7)
    chosen=choose_adaptive_modes(rows,order,spatial_shape,0 if predcode==6 else 1) if adaptive else None;mk=0
    for i,x in enumerate(rows):
        m=len(x)
        if not m:seqs.append(x);continue
        mode=int(chosen[mk]) if adaptive else int(predcode);mk+=1 if adaptive else 0
        p=predictor_for_mode(seqs,i,m,mode,order,spatial_shape);r=x-p;res.append(r.astype(np.int32));active_modes.append(mode);seqs.append(x)
    if adaptive and mk!=len(chosen):raise RuntimeError('adaptive mode accounting')
    R=np.concatenate(res) if res else np.empty(0,np.int32);M=np.asarray(active_modes,np.uint8)
    if R.size!=len(inter):raise RuntimeError(('residual count',R.size,len(inter)))
    if adaptive and style==1:
        symctx=np.repeat(M,mc[mc>0]);S,_=reorder_vals(R,symctx);Renc=S
    else:Renc=R
    raw_inter=leb_u(zz_enc(Renc));raw_modes=M.tobytes() if adaptive else b''
    diag={'predcode':int(predcode),'style':int(style),'adaptive':bool(adaptive),'residual_zero_fraction':float(np.mean(R==0)) if R.size else 0.0,'residual_mean_abs':float(np.mean(np.abs(R.astype(np.int64)))) if R.size else 0.0,'residual_p90_abs':float(np.quantile(np.abs(R.astype(np.int64)),.9)) if R.size else 0.0,'mode_counts':{str(k):int(v) for k,v in zip(*np.unique(M,return_counts=True))} if adaptive else {str(predcode):int(np.count_nonzero(mc))}}
    return raw_inter,raw_modes,diag


def restore_inter(rc,raw_inter,raw_modes,order,spatial_shape,predcode,style):
    mc=np.maximum(np.asarray(rc,np.int32)-1,0);n=int(mc.sum());adaptive=predcode in (6,7);na=int(np.count_nonzero(mc));M=np.frombuffer(raw_modes,np.uint8,count=na).copy() if adaptive else np.empty(0,np.uint8)
    Z=leb_dec(raw_inter,n);Renc=zz_dec(Z)
    if adaptive and style==1:
        symctx=np.repeat(M,mc[mc>0]);R=restore_vals(Renc,symctx).astype(np.int32)
    else:R=Renc
    off=np.r_[0,np.cumsum(mc,dtype=np.int64)];seqs=[];out=[];mk=0
    for i,m0 in enumerate(mc.tolist()):
        m=int(m0)
        if not m:seqs.append(np.empty(0,np.int32));continue
        mode=int(M[mk]) if adaptive else int(predcode);mk+=1 if adaptive else 0
        p=predictor_for_mode(seqs,i,m,mode,order,spatial_shape);r=R[off[i]:off[i+1]];x=p+r
        if np.any(x<0):raise RuntimeError(('negative reconstructed inter gap',i,mode,int(x.min())))
        x=x.astype(np.int32);out.append(x);seqs.append(x)
    if adaptive and mk!=len(M):raise RuntimeError('mode restore accounting')
    A=np.concatenate(out) if out else np.empty(0,np.int32)
    if A.size!=n:raise RuntimeError('inter restore accounting')
    return A


def encode_candidate(K,order,predcode,style):
    sh,dc,base_raw,base_meta=prepare_raw_frames(K,order,4);sh2,rc,startg,lens,rcomp,vals,phase,event_first,diag=gather_universal(K,order);rf=run_first_mask(rc);inter=startg[~rf]-2;spatial_shape=tuple(sh2[:-1])
    if predcode==0:
        raw_inter=base_raw[2];raw_modes=b'';pdiag={'predcode':0,'style':0,'baseline_context4':True}
    else:raw_inter,raw_modes,pdiag=transform_inter(rc,inter,order,spatial_shape,predcode,style)
    rawframes=[base_raw[0],base_raw[1],raw_inter,raw_modes,*base_raw[3:]];methods=[];frames=[];choices=[]
    for i,r in enumerate(rawframes):
        best,allrows=cached_best(r);n,m,b=best;methods.append(m);frames.append(b);choices.append({'frame':i,'raw_bytes':len(r),'chosen':METHOD_NAMES[m],'bytes':n,'all':allrows})
    oc=int(order[0]|(order[1]<<2)|(order[2]<<4));h=struct.pack(NHDR,NMAG,1,oc,dc,int(predcode),int(style),*K.shape,*methods,*[len(x) for x in frames]);names=['run_counts','first_starts','inter_payload','predictor_modes','long_support','very_support','long_residual','sign_first','sign_repeat','exception_support','exception_magnitude'];parts={names[i]:len(frames[i]) for i in range(11)};parts['timing_bytes']=sum(len(x) for x in frames[:7]);parts['value_bytes']=sum(len(x) for x in frames[7:]);parts['header_bytes']=NHS;parts['backend_choices']=choices;parts['predictor_diag']=pdiag;parts.update({k:v for k,v in base_meta.items() if k not in ('context_stats',)})
    return h+b''.join(frames),parts


def decode_candidate(blob):
    q=struct.unpack(NHDR,blob[:NHS]);magic,ver,oc,dc,predcode,style,C,L,S,T,*rest=q
    if magic!=NMAG or ver!=1:raise RuntimeError('neighbor predictor header')
    methods=rest[:11];lf=rest[11:];p=NHS;fs=[]
    for n in lf:fs.append(blob[p:p+n]);p+=n
    if p!=len(blob):raise RuntimeError('neighbor stream length')
    raw=[decomp_one(fs[i],methods[i]) for i in range(11)];order=tuple((oc>>(2*i))&3 for i in range(3));shape=(C,L,S,T);psh=tuple(shape[i] for i in order)+(T,);spatial_shape=psh[:-1];ntr=int(np.prod(spatial_shape));rc=leb_dec(raw[0],ntr);nr=int(rc.sum());rf=run_first_mask(rc);nn=int(np.count_nonzero(rc));firstcomp=first_components(rc,order,psh);firstg=first_restore(raw[1],nn,firstcomp,2)
    long=np.unpackbits(np.frombuffer(raw[4],np.uint8),bitorder='little',count=nr).astype(bool);nl=int(long.sum());very=np.unpackbits(np.frombuffer(raw[5],np.uint8),bitorder='little',count=nl).astype(bool) if nl else np.empty(0,bool);res=leb_dec(raw[6],int(very.sum())) if very.any() else np.empty(0,np.int32);runlens=np.ones(nr,np.int32);li=np.flatnonzero(long);runlens[li]=2
    if very.any():runlens[li[very]]=res+3
    if predcode==0:
        rcomp=run_components(rc,order,psh);ictx=inter_context(rc,runlens,rcomp,4);ss=leb_dec(raw[2],nr-nn);inter=restore_vals(ss,ictx).astype(np.int32)
    else:inter=restore_inter(rc,raw[2],raw[3],order,spatial_shape,int(predcode),int(style))
    startg=np.empty(nr,np.int32);startg[rf]=firstg;startg[~rf]=inter+2;rows=reconstruct_positions(rc,startg,runlens,T);counts,phase,event_first=metadata_from_positions(rows);ne=int(counts.sum())
    firstsign=np.unpackbits(np.frombuffer(raw[7],np.uint8),bitorder='little',count=nn).astype(bool);rep_mask=~event_first;rsort=np.unpackbits(np.frombuffer(raw[8],np.uint8),bitorder='little',count=ne-nn).astype(bool);repeat=restore_bits(rsort,phase[rep_mask]);signs=np.empty(ne,bool);k=fk=rk=0
    for c0 in counts.tolist():
        c=int(c0)
        if not c:continue
        s=bool(firstsign[fk]);fk+=1;signs[k]=s;k+=1
        for _ in range(1,c):
            if not repeat[rk]:s=not s
            rk+=1;signs[k]=s;k+=1
    if k!=ne or fk!=nn or rk!=repeat.size:raise RuntimeError('neighbor sign accounting')
    esort=np.unpackbits(np.frombuffer(raw[9],np.uint8),bitorder='little',count=ne).astype(bool);exc=restore_bits(esort,phase);nex=int(exc.sum());msort=np.frombuffer(raw[10],dtype=DT[dc],count=nex).astype(np.int32) if nex else np.empty(0,np.int32);mag=restore_vals(msort,phase[exc]) if nex else msort;ab=np.ones(ne,np.int32);ab[exc]=mag+2;vals=np.where(signs,-ab,ab);tr=np.zeros((ntr,T),np.int32);k=0
    for i,pos in enumerate(rows):
        c=pos.size
        if c:tr[i,pos]=vals[k:k+c];k+=c
    if k!=ne:raise RuntimeError('neighbor value accounting')
    P=tr.reshape(psh);inv=np.argsort(order);return np.transpose(P,tuple(inv)+(3,))


def main(path):
    order=(0,1,2);X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());eps=.1*std;step=2*eps;rawbytes=X.nbytes;G,tm,outids,geom=geometry_map(X,gx,gy)
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    O=np.rint(X[outids]/step).astype(np.int32);K=delta(G,3);rows=[]
    configs=[(0,0)]+[(m,0) for m in range(1,6)]+[(6,0),(6,1),(7,0),(7,1)]
    for predcode,style in configs:
        print('PRED',predcode,'STYLE',style,flush=True);b,parts=encode_candidate(K,order,predcode,style);R=decode_candidate(b)
        if not np.array_equal(R,K):raise RuntimeError(('neighbor exact K',predcode,style))
        rows.append({'main_bytes':len(b),'predcode':predcode,'style':style,'parts':parts,'blob':b});print(json.dumps({'main_bytes':len(b),'inter_bytes':parts['inter_payload'],'mode_bytes':parts['predictor_modes'],'diag':parts['predictor_diag']},indent=2),flush=True)
    rows.sort(key=lambda r:r['main_bytes']);best=rows[0];bo=best_out(O);RO=decode_out_best(bo,O.shape)
    if not np.array_equal(RO,O):raise RuntimeError('neighbor outlier decode')
    RG=undelta(decode_candidate(best['blob']),3);recon=np.empty_like(X)
    for tid,c,l,s in tm:recon[tid]=RG[c,l,s].astype(np.float32)*np.float32(step)
    recon[outids]=RO.astype(np.float32)*np.float32(step);me=float(np.max(np.abs(X-recon)));szb,sze=sz3_bytes(X,eps);container=TOPS+best['main_bytes']+int(bo[0]);baseline=133225
    out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':rawbytes,'eps':eps,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'main_best':{k:v for k,v in best.items() if k!='blob'},'main_candidates':[{k:v for k,v in r.items() if k!='blob'} for r in rows],'outlier_bytes':int(bo[0]),'top_header_bytes':TOPS,'container_bytes':container,'ratio':float(rawbytes/container),'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'sz3':{'bytes':int(szb),'ratio':float(rawbytes/szb),'maxerr':float(sze)},'gain_vs_direct_sz3':float(szb/container),'strongest_verified_p75_baseline_bytes':baseline,'gain_vs_strongest_verified_p75_baseline':float(baseline/container),'prior_record_bytes':63911,'improvement_vs_prior':63911-container}
    print(json.dumps({k:out[k] for k in ('container_bytes','ratio','maxerr','valid','gain_vs_direct_sz3','gain_vs_strongest_verified_p75_baseline','improvement_vs_prior')},indent=2),flush=True);json.dump(out,open('soda_run_gap_neighbor_predictor.json','w'),indent=2)

main(sys.argv[1])
