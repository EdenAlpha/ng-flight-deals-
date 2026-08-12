import json,os,struct,sys
import numpy as np

# Reuse PR #189's exact refined run/Rice codec, geometry, outlier dictionary,
# backend menu and no-phase/phase incumbents without running its CLI.
src=open('research/soda_tight_refined_context_phase.py').read().rsplit('\nmain(sys.argv[1],float(sys.argv[2]))',1)[0]
exec(compile(src,'soda_tight_refined_context_phase.py','exec'),globals())

FMAG=b'FNORM001'
FHDR='<8sddBBBQQQ'
FHS=struct.calcsize(FHDR)
PMODES={0:'none',1:'run-phase',2:'component',3:'component-x-phase',4:'phase-x-sign',5:'component-x-phase-x-sign'}


def minchange_trace(x,eps,step):
    xd=x.astype(np.float64,copy=False);lo=np.ceil((xd-eps)/step-1e-12).astype(np.int32);hi=np.floor((xd+eps)/step+1e-12).astype(np.int32)
    if np.any(lo>hi):raise RuntimeError('empty legal fine-state interval')
    n=x.size;segs=[];a=0;L=int(lo[0]);H=int(hi[0])
    for t in range(1,n):
        nL=max(L,int(lo[t]));nH=min(H,int(hi[t]))
        if nL<=nH:L,H=nL,nH
        else:segs.append((a,t,L,H));a=t;L=int(lo[t]);H=int(hi[t])
    segs.append((a,n,L,H));q=np.empty(n,np.int32);prev=None
    for a,b,L,H in segs:
        v=int(np.clip(0 if prev is None else prev,L,H));q[a:b]=v;prev=v
    me=float(np.max(np.abs(xd-q.astype(np.float64)*step)))
    if me>eps*(1+1e-10):raise RuntimeError(('fine-state legality',me,eps,step))
    return q,len(segs)


def build_fine_main(X,tm,shape,eps):
    step=eps;G=np.zeros(shape,np.int32);segments=0
    for tid,c,l,s in tm:
        q,n=minchange_trace(X[tid],eps,step);G[c,l,s]=q;segments+=n
    return G,step,segments


def normalize_delta(D,scale=2):
    a=np.abs(D.astype(np.int64));vabs=(a+scale-1)//scale;V=(np.sign(D).astype(np.int64)*vabs).astype(np.int32);R=(scale*vabs-a).astype(np.uint8)
    # scale=2 -> R is exactly odd/even correction: |D|=2|V|-R.
    if scale!=2 or np.any(R>1):raise RuntimeError('factorized remainder range')
    if not np.array_equal(V!=0,D!=0):raise RuntimeError('factorized support changed')
    return V,R


def event_context(V,mode):
    sh,rc,startg,lens,rcomp,vals,phase,event_first,diag=gather_universal(V,ORDER);comp=np.repeat(rcomp.astype(np.int32),lens.astype(np.int64));sign=(vals<0).astype(np.int32)
    if comp.size!=vals.size:raise RuntimeError('factorized event-component accounting')
    if mode==0:ctx=np.zeros(vals.size,np.int32)
    elif mode==1:ctx=phase.astype(np.int32)
    elif mode==2:ctx=comp
    elif mode==3:ctx=comp*4+phase.astype(np.int32)
    elif mode==4:ctx=phase.astype(np.int32)*2+sign
    elif mode==5:ctx=(comp*4+phase.astype(np.int32))*2+sign
    else:raise ValueError(mode)
    return ctx,vals,phase,comp


def encode_parity(V,D):
    ctx0,vals,phase,comp=event_context(V,0)
    if not np.array_equal(V[V!=0],vals):raise RuntimeError('factorized event order mismatch')
    dvals=D[D!=0].astype(np.int64)
    if dvals.size!=vals.size:raise RuntimeError('factorized D event count')
    parity=(np.abs(dvals)&1).astype(bool);rows=[]
    for mode,name in PMODES.items():
        ctx,vals2,_,_=event_context(V,mode)
        if not np.array_equal(vals2,vals):raise RuntimeError('factorized context event order')
        s,_=reorder_bits(parity,ctx);raw=np.packbits(s,bitorder='little').tobytes();best,allrows=best_comp(raw);n,m,b=best;rows.append((n,mode,m,b,raw,ctx,allrows))
    rows.sort(key=lambda r:(r[0],r[1],r[2]));w=rows[0]
    return w[3],int(w[1]),int(w[2]),{'mode':int(w[1]),'name':PMODES[int(w[1])],'bytes':int(w[0]),'raw_packed_bytes':len(w[4]),'ones_fraction':float(parity.mean()) if parity.size else 0.0,'contexts':int(np.max(w[5]))+1 if w[5].size else 1,'backend':METHOD_NAMES[int(w[2])],'candidates':[{'mode':int(r[1]),'name':PMODES[int(r[1])],'bytes':int(r[0]),'backend':METHOD_NAMES[int(r[2])]} for r in rows]}


def decode_parity(V,blob,mode,method):
    ctx,vals,_,_=event_context(V,mode);raw=decomp_one(blob,method);s=np.unpackbits(np.frombuffer(raw,np.uint8),bitorder='little',count=vals.size).astype(bool);p=restore_bits(s,ctx)
    return p,vals


def restore_fine_delta(V,parity):
    p=np.asarray(parity,np.int64);vals=V[V!=0].astype(np.int64)
    if vals.size!=p.size:raise RuntimeError('factorized parity length')
    a=2*np.abs(vals)-p
    if np.any(a<=0):raise RuntimeError('factorized restored zero event')
    dvals=np.sign(vals)*a;D=np.zeros_like(V,np.int32);D[V!=0]=dvals.astype(np.int32)
    return D


def decode_out_coarse(blob,kind,td,Oshape):
    if kind==0:
        A=decode(blob).reshape(Oshape);return undelta(A,1) if td else A
    if kind==1:
        A=decode_out_sparse(blob);return undelta(A,1) if td else A
    raise RuntimeError(('factorized outlier kind',kind))


def encode_top(internal_eps,fine_step,mb,pb,pmode,pmethod,bo):
    ob=bo[6];ok=0 if bo[1]=='gap' else 1;td=1 if bo[2] else 0;ocode=ok|(td<<1)
    h=struct.pack(FHDR,FMAG,float(internal_eps),float(fine_step),int(pmode),int(pmethod),int(ocode),len(mb),len(pb),len(ob));return h+mb+pb+ob


def decode_top(blob,Oshape):
    q=struct.unpack(FHDR,blob[:FHS]);magic,eps,step,pmode,pmethod,ocode,lm,lp,lo=q
    if magic!=FMAG:raise RuntimeError('factorized top magic')
    p=FHS;mb=blob[p:p+lm];p+=lm;pb=blob[p:p+lp];p+=lp;ob=blob[p:p+lo];p+=lo
    if p!=len(blob):raise RuntimeError('factorized top length')
    V=decode_refined_main(mb);parity,vals=decode_parity(V,pb,pmode,pmethod);D=restore_fine_delta(V,parity);RO=decode_out_coarse(ob,ocode&1,(ocode>>1)&1,Oshape)
    return float(eps),float(step),V,D,RO


def main(path):
    frac=.05;X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());public_eps=frac*std;internal_eps=public_eps*INTERNAL_SAFETY;raw=int(X.nbytes);G0,tm,outids,geom=geometry_map(X,gx,gy);szb,sze=sz3_bytes(X,public_eps)
    # Exact current frontiers on identical input.
    inc0=eval_no_phase(X,tm,outids,G0.shape,internal_eps);incp=eval_phase(X,tm,outids,G0.shape,internal_eps);inc=min(inc0['container_bytes'],incp['container_bytes'])
    # Fine minimum-change main grid at step=internal_eps (half the incumbent 2eps spacing).
    G,fine_step,segments=build_fine_main(X,tm,G0.shape,internal_eps);D=delta(G,3);V,R=normalize_delta(D,2);mb,parts=prepare_refined_main(V);RV=decode_refined_main(mb)
    if not np.array_equal(RV,V):raise RuntimeError('factorized normalized V decode')
    pb,pmode,pmethod,pdiag=encode_parity(V,D)
    # Keep outliers on the robust coarse nearest-state representation; no fine-lattice overhead there.
    O=np.rint(X[outids].astype(np.float64)/(2*internal_eps)).astype(np.int32);bo=best_out(O);RO=decode_out_exact(bo,O.shape)
    if not np.array_equal(RO,O):raise RuntimeError('factorized coarse outlier decode')
    top=encode_top(internal_eps,fine_step,mb,pb,pmode,pmethod,bo);ee,ss,DV,RD,RO2=decode_top(top,O.shape)
    if not np.array_equal(DV,V) or not np.array_equal(RD,D) or not np.array_equal(RO2,O):raise RuntimeError('factorized exact integer top decode')
    Q=np.cumsum(RD,axis=3,dtype=np.int64).astype(np.int32);Y=np.empty_like(X)
    for tid,c,l,s in tm:Y[tid]=Q[c,l,s].astype(np.float32)*np.float32(ss)
    Y[outids]=RO2.astype(np.float32)*np.float32(2*ee);me=float(np.max(np.abs(X-Y)));valid=bool(me<=public_eps*(1+3e-6))
    if not valid:raise RuntimeError(('factorized hard error',me,public_eps,ee,ss))
    # Baseline nearest K density for mechanism diagnosis.
    BG=np.zeros_like(G)
    for tid,c,l,s in tm:BG[c,l,s]=np.rint(X[tid].astype(np.float64)/(2*internal_eps)).astype(np.int32)
    BK=delta(BG,3)
    out={'file':os.path.basename(path),'shape':list(X.shape),'epsilon_fraction_of_std':frac,'public_eps':public_eps,'internal_eps':internal_eps,'raw_bytes':raw,'geometry':geom,'incumbent_no_phase_bytes':int(inc0['container_bytes']),'incumbent_phase_bytes':int(incp['container_bytes']),'incumbent_best_bytes':int(inc),'fine_step':fine_step,'fine_segments':int(segments),'baseline_K_nonzero_fraction':float(np.mean(BK!=0)),'fine_D_nonzero_fraction':float(np.mean(D!=0)),'event_reduction_vs_nearest':float(1-np.count_nonzero(D)/max(1,np.count_nonzero(BK))),'normalized_V_abs_mean_events':float(np.mean(np.abs(V[V!=0]).astype(np.float64))) if np.any(V) else 0.0,'main_bytes':len(mb),'main_parts':parts,'parity_bytes':len(pb),'parity_diag':pdiag,'outlier_bytes':int(bo[0]),'top_header_bytes':FHS,'container_bytes':len(top),'ratio':float(raw/len(top)),'improvement_vs_incumbent':float(inc/len(top)),'saving_vs_incumbent_bytes':int(inc-len(top)),'sz3':{'bytes':int(szb),'ratio':float(raw/szb),'maxerr':float(sze)},'gain_vs_direct_sz3':float(szb/len(top)),'two_x_target_bytes':szb/2,'clears_2x':bool(len(top)<=szb/2),'maxerr':me,'valid':valid}
    print(json.dumps({'incumbent':inc,'factorized_bytes':len(top),'saving':out['saving_vs_incumbent_bytes'],'event_reduction':out['event_reduction_vs_nearest'],'baseline_K_nz':out['baseline_K_nonzero_fraction'],'fine_D_nz':out['fine_D_nonzero_fraction'],'normalized_event_abs_mean':out['normalized_V_abs_mean_events'],'parity_bytes':len(pb),'parity_ones':pdiag['ones_fraction'],'gain_sz3':out['gain_vs_direct_sz3'],'target':out['two_x_target_bytes'],'clears_2x':out['clears_2x'],'maxerr':me,'eps':public_eps},indent=2),flush=True);json.dump(out,open('soda_tight_factorized_state.json','w'),indent=2)

main(sys.argv[1])
