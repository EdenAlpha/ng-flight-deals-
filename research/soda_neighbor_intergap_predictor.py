import json,os,struct,sys
import numpy as np

# Reuse PR #161's exact frame backends, PR #158 contexts, and all audited
# geometry/run/value/outlier/fidelity machinery. Only the 71,547-symbol
# inter-run (g-2) frame is transformed here.
src=open('research/soda_intergap_backend_hybrid.py').read().split('\ndef main(path):')[0]
exec(compile(src,'soda_intergap_backend_hybrid.py','exec'),globals())

PMAG=b'IGPRD001'
PHDR='<8sBBBB4I10B10Q'
PHS=struct.calcsize(PHDR)


def zz_enc_scalar(x):
    x=int(x);return 2*x if x>=0 else -2*x-1

def zz_dec_scalar(u):
    u=int(u);return u//2 if (u&1)==0 else -(u//2)-1

def split_inter(rc,flat):
    out=[];k=0
    for n0 in rc.tolist():
        m=max(0,int(n0)-1);out.append(np.asarray(flat[k:k+m],np.int32));k+=m
    if k!=len(flat):raise RuntimeError(('split inter',k,len(flat)))
    return out

def flatten_inter(rows):
    if not rows:return np.empty(0,np.int32)
    return np.concatenate([r for r in rows if r.size]).astype(np.int32) if any(r.size for r in rows) else np.empty(0,np.int32)

def neighbor_index(i,order,psh,orig_axis):
    ax=order.index(orig_axis);coord=list(np.unravel_index(i,psh[:-1]))
    if coord[ax]<=0:return -1
    coord[ax]-=1;return int(np.ravel_multi_index(tuple(coord),psh[:-1]))

def pick_predictor(mode,i,j,decoded,rc,order,psh):
    # mode 1: previous gap in same trace
    if mode==1:return int(decoded[i][j-1]) if j>0 else 0
    cand=[]
    if mode in (2,5,6,7,8):
        q=neighbor_index(i,order,psh,2)
        if q>=0 and j<decoded[q].size:cand.append(('station',int(decoded[q][j])))
    if mode in (3,5,6,7,8):
        q=neighbor_index(i,order,psh,1)
        if q>=0 and j<decoded[q].size:cand.append(('line',int(decoded[q][j])))
    if mode in (4,5,7,8):
        q=neighbor_index(i,order,psh,0)
        if q>=0 and j<decoded[q].size:cand.append(('component',int(decoded[q][j])))
    prev=int(decoded[i][j-1]) if j>0 else None
    if mode==2:return cand[0][1] if cand else 0
    if mode==3:return cand[0][1] if cand else 0
    if mode==4:return cand[0][1] if cand else 0
    if mode==5:
        # deterministic priority: station, line, component, then temporal.
        if cand:return cand[0][1]
        return prev if prev is not None else 0
    if mode==6:
        vals=[v for name,v in cand if name in ('station','line')]
        if len(vals)>=2:return int((vals[0]+vals[1])//2)
        if vals:return vals[0]
        return prev if prev is not None else 0
    if mode==7:
        vals=[v for _,v in cand]
        if prev is not None:vals.append(prev)
        if not vals:return 0
        vals=sorted(vals);return int(vals[(len(vals)-1)//2])
    if mode==8:
        # choose the physical neighbour whose run count is closest to current;
        # this rule is fully decoder-visible from rc.
        opts=[]
        for axis,name in ((2,'station'),(1,'line'),(0,'component')):
            q=neighbor_index(i,order,psh,axis)
            if q>=0 and j<decoded[q].size:opts.append((abs(int(rc[i])-int(rc[q])),axis,int(decoded[q][j])))
        if opts:return min(opts,key=lambda x:(x[0],x[1]))[2]
        return prev if prev is not None else 0
    raise ValueError(mode)

def predictor_name(mode):
    return {0:'absolute-gminus2',1:'previous-intergap',2:'previous-station-rank',3:'previous-line-rank',4:'previous-component-rank',5:'station-line-component-fallback',6:'station-line-average',7:'causal-neighbour-median',8:'closest-run-count-neighbour'}[mode]

def encode_inter(inter,rc,order,psh,ictx,mode):
    if mode==0:
        s,_=reorder_vals(inter,ictx);return leb_u(s),{'residual_zero_fraction':float(np.mean(inter==0)) if inter.size else 0.0,'mean_abs_residual':float(np.mean(np.abs(inter))) if inter.size else 0.0}
    actual=split_inter(rc,inter);decoded=[np.empty_like(r) for r in actual];res=[]
    for i,row in enumerate(actual):
        for j,x0 in enumerate(row.tolist()):
            p=pick_predictor(mode,i,j,decoded,rc,order,psh);x=int(x0);res.append(x-p);decoded[i][j]=x
    res=np.asarray(res,np.int32)
    if res.size!=inter.size:raise RuntimeError('predictor encode count')
    u=np.asarray([zz_enc_scalar(x) for x in res.tolist()],np.int32);s,_=reorder_vals(u,ictx)
    return leb_u(s),{'residual_zero_fraction':float(np.mean(res==0)) if res.size else 0.0,'mean_abs_residual':float(np.mean(np.abs(res))) if res.size else 0.0,'p50_abs_residual':float(np.median(np.abs(res))) if res.size else 0.0,'p90_abs_residual':float(np.quantile(np.abs(res),.9)) if res.size else 0.0}

def decode_inter(buf,rc,order,psh,ictx,mode):
    n=int(np.sum(np.maximum(rc.astype(np.int64)-1,0)))
    s=leb_dec(buf,n);u=restore_vals(s,ictx).astype(np.int32)
    if mode==0:return u
    residual=np.asarray([zz_dec_scalar(v) for v in u.tolist()],np.int32);decoded=[np.empty(max(0,int(x)-1),np.int32) for x in rc.tolist()];k=0
    for i,row in enumerate(decoded):
        for j in range(row.size):
            p=pick_predictor(mode,i,j,decoded,rc,order,psh);x=p+int(residual[k]);k+=1
            if x<0:raise RuntimeError(('negative reconstructed g-2',mode,i,j,x))
            row[j]=x
    if k!=n:raise RuntimeError('predictor decode count')
    return flatten_inter(decoded)

def common_and_predictor(K,order=(0,1,2),ctxmode=4):
    sh,dc,rawframes,meta=prepare_raw_frames(K,order,ctxmode)
    sh2,rc,startg,lens,rcomp,vals,phase,event_first,diag=gather_universal(K,order)
    if tuple(sh2)!=tuple(sh):raise RuntimeError('shape disagreement')
    rf=run_first_mask(rc);inter=(startg[~rf]-2).astype(np.int32);ictx=inter_context(rc,lens,rcomp,ctxmode);psh=tuple(sh)
    # Assert predictor-mode zero reproduces PR #161's exact raw frame.
    chk,_=encode_inter(inter,rc,order,psh,ictx,0)
    if chk!=rawframes[2]:raise RuntimeError('baseline inter frame mismatch')
    return sh,dc,rawframes,meta,rc,lens,rcomp,inter,ictx,psh

def encode_candidate(K,predmode,order=(0,1,2),ctxmode=4,cache=None):
    if cache is None:cache=common_and_predictor(K,order,ctxmode)
    sh,dc,rawframes,meta,rc,lens,rcomp,inter,ictx,psh=cache
    raw2,pdiag=encode_inter(inter,rc,order,psh,ictx,predmode);frames=[];methods=[];choices=[]
    for i,r0 in enumerate(rawframes):
        r=raw2 if i==2 else r0;best,allrows=best_comp(r);n,m,b=best;methods.append(m);frames.append(b);choices.append({'frame':i,'raw_bytes':len(r),'chosen':METHOD_NAMES[m],'bytes':n,'all':allrows})
    oc=int(order[0]|(order[1]<<2)|(order[2]<<4));code=int(ctxmode)|(int(predmode)<<4);h=struct.pack(PHDR,PMAG,1,oc,dc,code,*K.shape,*methods,*[len(x) for x in frames]);names=['run_counts','first_starts','inter_starts','long_support','very_support','long_residual','sign_first','sign_repeat','exception_support','exception_magnitude'];parts={names[i]:len(frames[i]) for i in range(10)};parts['timing_bytes']=sum(len(x) for x in frames[:6]);parts['value_bytes']=sum(len(x) for x in frames[6:]);parts['header_bytes']=PHS;parts['backend_choices']=choices;parts['context_mode']=ctxmode;parts['predictor_mode']=predmode;parts['predictor_name']=predictor_name(predmode);parts['predictor_diag']=pdiag;parts.update({k:v for k,v in meta.items() if k not in ('context_mode',)})
    return h+b''.join(frames),parts

def decode_candidate(blob):
    q=struct.unpack(PHDR,blob[:PHS]);magic,ver,oc,dc,code,C,L,S,T,*rest=q
    if magic!=PMAG or ver!=1:raise RuntimeError('predictor header')
    ctxmode=int(code)&15;predmode=int(code)>>4;methods=rest[:10];lf=rest[10:];p=PHS;frames=[]
    for n in lf:frames.append(blob[p:p+n]);p+=n
    if p!=len(blob):raise RuntimeError('predictor stream length')
    raw=[decomp_one(frames[i],methods[i]) for i in range(10)];order=tuple((oc>>(2*i))&3 for i in range(3));shape=(C,L,S,T);psh=tuple(shape[i] for i in order)+(T,);ntr=int(np.prod(psh[:-1]));rc=leb_dec(raw[0],ntr);nr=int(rc.sum());rf=run_first_mask(rc);nn=int(np.count_nonzero(rc));firstcomp=first_components(rc,order,psh);firstg=first_restore(raw[1],nn,firstcomp,2)
    long=np.unpackbits(np.frombuffer(raw[3],np.uint8),bitorder='little',count=nr).astype(bool);nl=int(long.sum());very=np.unpackbits(np.frombuffer(raw[4],np.uint8),bitorder='little',count=nl).astype(bool) if nl else np.empty(0,bool);res=leb_dec(raw[5],int(very.sum())) if very.any() else np.empty(0,np.int32);runlens=np.ones(nr,np.int32);li=np.flatnonzero(long);runlens[li]=2
    if very.any():runlens[li[very]]=res+3
    rcomp=run_components(rc,order,psh);ictx=inter_context(rc,runlens,rcomp,ctxmode);inter=decode_inter(raw[2],rc,order,psh,ictx,predmode);startg=np.empty(nr,np.int32);startg[rf]=firstg;startg[~rf]=inter+2;rows=reconstruct_positions(rc,startg,runlens,T);counts,phase,event_first=metadata_from_positions(rows);ne=int(counts.sum())
    firstsign=np.unpackbits(np.frombuffer(raw[6],np.uint8),bitorder='little',count=nn).astype(bool);rep_mask=~event_first;rsort=np.unpackbits(np.frombuffer(raw[7],np.uint8),bitorder='little',count=ne-nn).astype(bool);repeat=restore_bits(rsort,phase[rep_mask]);signs=np.empty(ne,bool);k=fk=rk=0
    for c0 in counts.tolist():
        c=int(c0)
        if not c:continue
        s=bool(firstsign[fk]);fk+=1;signs[k]=s;k+=1
        for _ in range(1,c):
            if not repeat[rk]:s=not s
            rk+=1;signs[k]=s;k+=1
    if k!=ne or fk!=nn or rk!=repeat.size:raise RuntimeError('predictor sign accounting')
    esort=np.unpackbits(np.frombuffer(raw[8],np.uint8),bitorder='little',count=ne).astype(bool);exc=restore_bits(esort,phase);nex=int(exc.sum());msort=np.frombuffer(raw[9],dtype=DT[dc],count=nex).astype(np.int32) if nex else np.empty(0,np.int32);mag=restore_vals(msort,phase[exc]) if nex else msort;ab=np.ones(ne,np.int32);ab[exc]=mag+2;vals=np.where(signs,-ab,ab);tr=np.zeros((ntr,T),np.int32);k=0
    for i,pos in enumerate(rows):
        c=pos.size
        if c:tr[i,pos]=vals[k:k+c];k+=c
    if k!=ne:raise RuntimeError('predictor value accounting')
    P=tr.reshape(psh);inv=np.argsort(order);return np.transpose(P,tuple(inv)+(3,))

def main(path):
    order=(0,1,2);ctxmode=4;X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());eps=.1*std;step=2*eps;rawbytes=X.nbytes;G,tm,outids,geom=geometry_map(X,gx,gy)
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    O=np.rint(X[outids]/step).astype(np.int32);K=delta(G,3);cache=common_and_predictor(K,order,ctxmode);rows=[]
    for predmode in range(9):
        print('PREDICTOR',predmode,predictor_name(predmode),flush=True);b,parts=encode_candidate(K,predmode,order,ctxmode,cache);RK=decode_candidate(b)
        if not np.array_equal(RK,K):raise RuntimeError(('predictor exact K',predmode))
        rows.append({'predictor_mode':predmode,'predictor_name':predictor_name(predmode),'main_bytes':len(b),'parts':parts,'blob':b});print(json.dumps({'mode':predmode,'name':predictor_name(predmode),'main_bytes':len(b),'inter_bytes':parts['inter_starts'],'timing_bytes':parts['timing_bytes'],'diag':parts['predictor_diag']},indent=2),flush=True)
    rows.sort(key=lambda x:x['main_bytes']);best=rows[0];RK=decode_candidate(best['blob']);bo=best_out(O);RO=decode_out_best(bo,O.shape)
    if not np.array_equal(RO,O):raise RuntimeError('predictor outlier decode')
    RG=undelta(RK,3);recon=np.empty_like(X)
    for tid,c,l,s in tm:recon[tid]=RG[c,l,s].astype(np.float32)*np.float32(step)
    recon[outids]=RO.astype(np.float32)*np.float32(step);me=float(np.max(np.abs(X-recon)));szb,sze=sz3_bytes(X,eps);container=TOPS+best['main_bytes']+int(bo[0]);baseline=133225
    out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':rawbytes,'eps':eps,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'best':{k:v for k,v in best.items() if k!='blob'},'candidates':[{k:v for k,v in r.items() if k!='blob'} for r in rows],'outlier_bytes':int(bo[0]),'top_header_bytes':TOPS,'container_bytes':container,'ratio':float(rawbytes/container),'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'sz3':{'bytes':int(szb),'ratio':float(rawbytes/szb),'maxerr':float(sze)},'gain_vs_direct_sz3':float(szb/container),'strongest_verified_p75_baseline_bytes':baseline,'gain_vs_strongest_verified_p75_baseline':float(baseline/container),'prior_pr161_bytes':63911,'improvement_vs_pr161_bytes':int(63911-container)}
    print(json.dumps({k:out[k] for k in ('container_bytes','ratio','gain_vs_direct_sz3','gain_vs_strongest_verified_p75_baseline','improvement_vs_pr161_bytes','maxerr','valid')},indent=2),flush=True);json.dump(out,open('soda_neighbor_intergap_predictor.json','w'),indent=2)

main(sys.argv[1])
