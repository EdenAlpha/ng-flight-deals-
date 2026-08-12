import json,math,sys
import h5py,numpy as np
import imperial_decoder_phase_automaton as m
import imperial_dyadic_shared_resonator as ar

SAFETY=1-1e-5
ORDER=16

def predict_float(R,c,t,coef,p):
    if t<p:return 0.0
    v=float(coef[-1])
    for j in range(p):v+=float(coef[j])*float(R[c,t-1-j])
    if not math.isfinite(v):raise RuntimeError(('nonfinite',c,t))
    return v

def encode_nearest(X,eps):
    step=2*eps*SAFETY
    K=np.rint(X/step).astype(np.int32)
    frame=m.encode_k(K);Kd=frame[2]
    R=step*Kd.astype(np.float64)
    me=float(np.max(np.abs(X-R)))
    if me>eps*(1+2e-6):raise RuntimeError(('nearest hard',me,eps))
    return {'bytes':int(frame[0])+32,'bps':8*(int(frame[0])+32)/X.size,'rep':frame[1],'step':step,'maxerr':me,'k_std':float(K.std()),'k_zero_fraction':float(np.mean(K==0))}

def encode_ar16(X,eps):
    step=2*eps*SAFETY
    co=ar.fit_shared(X,ORDER);mb,cd=ar.model_frame(co)
    R=np.zeros(X.shape,np.float64);K=np.zeros(X.shape,np.int32)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):
            p=predict_float(R,c,t,cd,ORDER);k=int(np.rint((float(X[c,t])-p)/step));R[c,t]=p+step*k;K[c,t]=k
    me=float(np.max(np.abs(X-R)))
    if me>eps*(1+2e-6):raise RuntimeError(('encode hard',me,eps))
    frame=m.encode_k(K);Kd=frame[2]
    Rd=np.zeros_like(R)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):
            p=predict_float(Rd,c,t,cd,ORDER);Rd[c,t]=p+step*int(Kd[c,t])
    if not np.allclose(Rd,R,rtol=0,atol=1e-9):raise RuntimeError('recursive float decode mismatch')
    me2=float(np.max(np.abs(X-Rd)))
    if me2>eps*(1+2e-6):raise RuntimeError(('decode hard',me2,eps))
    total=int(mb)+int(frame[0])+48
    return {'bytes':total,'bps':8*total/X.size,'model_bytes':int(mb),'innovation_bytes':int(frame[0]),'rep':frame[1],'step':step,'maxerr':me2,'k_std':float(K.std()),'k_zero_fraction':float(np.mean(K==0)),'coefficients':cd.tolist()}

def run_mode(X,eps):
    sb,ori=m.szrun(X,eps)
    near=encode_nearest(X,eps);a=encode_ar16(X,eps)
    for r in (near,a):r['gain_vs_sz3']=sb/r['bytes']
    return {'eps':eps,'sz3_bytes':sb,'sz3_bps':8*sb/X.size,'sz3_orientation':ori,'nearest':near,'ar16':a}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=m.stats(d);geps=.1*gstd;rows=[]
        for name,t0,c0 in m.SPECS:
            X=np.asarray(d[t0:t0+m.T,c0:c0+m.C],np.float64).T
            lstd=float(X.std());leps=.1*lstd
            local=run_mode(X,leps)
            # Global result is included only as an internal reference on the same tile;
            # it is not mixed with the locally normalized comparison.
            glob=run_mode(X,geps)
            row={'tile':name,'t0':t0,'c0':c0,'samples':int(X.size),'local_std':lstd,'global_std':gstd,'local_eps_10pct':leps,'global_eps_10pct':geps,'global_eps_as_fraction_local_std':geps/lstd,'local_normalized':local,'global_reference':glob}
            rows.append(row)
            print(json.dumps({'tile':name,'local_eps':leps,'global_eps/local_std':geps/lstd,'local_sz3_bps':local['sz3_bps'],'local_nearest_bps':local['nearest']['bps'],'local_nearest_gain':local['nearest']['gain_vs_sz3'],'local_ar16_bps':local['ar16']['bps'],'local_ar16_gain':local['ar16']['gain_vs_sz3'],'global_ar16_gain_reference':glob['ar16']['gain_vs_sz3']},indent=2),flush=True)
        def aggregate(which,codec):
            sb=sum(r[which]['sz3_bytes'] for r in rows);cb=sum(r[which][codec]['bytes'] for r in rows);n=sum(r['samples'] for r in rows)
            return {'codec':codec,'bytes':cb,'sz3_bytes':sb,'bps':8*cb/n,'sz3_bps':8*sb/n,'gain_vs_sz3':sb/cb,'strict_2x_target_bps':(8*sb/n)/2,'ratio_to_2x_target':(8*cb/n)/((8*sb/n)/2),'min_tile_gain':min(r[which][codec]['gain_vs_sz3'] for r in rows)}
        out={'global_std':gstd,'global_eps_10pct':geps,'patch_shape':[m.C,m.T],'rows':rows,'local_normalized_aggregate':[aggregate('local_normalized','nearest'),aggregate('local_normalized','ar16')],'global_reference_aggregate':[aggregate('global_reference','nearest'),aggregate('global_reference','ar16')],'scope':'Separate fidelity-normalization experiment; DO NOT compare its compression ratios as if they used the original global-epsilon contract. Each 128x1024 tile gets eps=0.10*that exact tile standard deviation, so hard/easy/medium/far regions are evaluated at the same normalized maximum-error level. Matched SZ3 receives exactly the same local epsilon. Our deterministic candidates are a nearest legal lattice with spacing 2*eps*(1-1e-5) and a shared float32-serialized AR16 recursive predictor whose only payload beyond the model is the exact integer lattice-innovation field through the existing self-decoding representation menu. Every decoded sample is independently checked against its local hard bound. For diagnosis only, the original global-epsilon result is rerun separately on the same tiles. This tests whether global-std normalization itself created severe local-fidelity imbalance; it does not replace or solve the original global-epsilon benchmark.'}
        print(json.dumps({'local_normalized_aggregate':out['local_normalized_aggregate'],'global_reference_aggregate':out['global_reference_aggregate']},indent=2),flush=True)
        json.dump(out,open('imperial_local_normalized_harderror_gate.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
