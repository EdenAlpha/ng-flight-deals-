import json,sys
import h5py,numpy as np
import imperial_decoder_phase_automaton as m
import imperial_dyadic_shared_resonator as ar

KS=(0,4,8,16,24,32,40,48,56,64,72,80,88,96,104,112,120,124,126,127,128)
ORDER=16

def entropy_int(a):
    _,n=np.unique(np.asarray(a).ravel(),return_counts=True)
    p=n.astype(np.float64)/n.sum()
    return float(-(p*np.log2(p)).sum())

def predictor_and_residual(X):
    co=ar.fit_shared(X,ORDER)
    _,cd=ar.model_frame(co)
    P=np.zeros(X.shape,np.int32)
    R=np.zeros(X.shape,np.int32)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):
            pred=ar.predict_hist(R,c,t,cd,ORDER,'shared')
            k=int(np.rint((float(X[c,t])-pred)/m.STEP))
            P[c,t]=pred
            R[c,t]=pred+m.STEP*k
    E=X-P.astype(np.float64)
    return P,E,cd

def evaluate_tile(X,eps,sz3_bytes):
    P,E,coef=predictor_and_residual(X)
    U,s,Vt=np.linalg.svd(E,full_matrices=False)
    total_energy=float(np.dot(s,s))
    rows=[]
    target_bytes=sz3_bytes/2.0
    for k in KS:
        if k==0:
            Ck=np.zeros_like(E)
        else:
            Ck=(U[:,:k]*s[:k])@Vt[:k]
        N=E-Ck
        K=np.rint(N/m.STEP).astype(np.int32)
        frame=m.encode_k(K)
        Kd=frame[2].astype(np.int32)
        R=P.astype(np.float64)+Ck+m.STEP*Kd.astype(np.float64)
        me=float(np.max(np.abs(X-R)))
        if me>128.000001 or me>eps*(1+1e-12):
            raise RuntimeError(('oracle hard error',k,me,eps))
        b=int(frame[0])+16
        rem_energy=float(np.sum(s[k:]**2)) if k<len(s) else 0.0
        rows.append({
            'free_modes':k,
            'charged_bytes':b,
            'charged_bps':8*b/X.size,
            'innovation_rep':frame[1],
            'gain_vs_sz3':sz3_bytes/b,
            'ratio_to_strict_2x_target':b/target_bytes,
            'crosses_2x_target':bool(b<=target_bytes),
            'innovation_zero_order_entropy_bps':entropy_int(K),
            'innovation_std':float(K.std()),
            'innovation_zero_fraction':float(np.mean(K==0)),
            'innovation_abs_le1_fraction':float(np.mean(np.abs(K)<=1)),
            'residual_energy_fraction_left':rem_energy/total_energy if total_energy else 0.0,
            'free_mode_energy_fraction':1.0-rem_energy/total_energy if total_energy else 1.0,
            'maxerr':me
        })
    first_actual=next((r for r in rows if r['crosses_2x_target']),None)
    # Entropy-only crossing is even more optimistic than real frame bytes.
    target_bps=4*sz3_bytes/X.size
    first_entropy=next((r for r in rows if r['innovation_zero_order_entropy_bps']<=target_bps),None)
    return rows,{
        'strict_2x_target_bytes':target_bytes,
        'strict_2x_target_bps':target_bps,
        'first_free_modes_crossing_actual_bytes':None if first_actual is None else first_actual['free_modes'],
        'first_free_modes_crossing_zero_order_entropy':None if first_entropy is None else first_entropy['free_modes'],
        'singular_values':s.tolist(),
        'ar16_coefficients_free_oracle':coef.tolist()
    }

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;allrows=[];tiles=[]
        for name,t0,c0 in m.SPECS:
            X=np.asarray(d[t0:t0+m.T,c0:c0+m.C],np.float64).T
            sb,ori=m.szrun(X,eps)
            rr,audit=evaluate_tile(X,eps,sb)
            for r in rr:
                r.update({'tile':name,'t0':t0,'c0':c0,'sz3_bytes':sb,'sz3_bps':8*sb/X.size})
                allrows.append(r)
            tiles.append({'tile':name,'t0':t0,'c0':c0,'samples':int(X.size),'local_std':float(X.std()),'sz3_bytes':sb,'sz3_bps':8*sb/X.size,'sz3_orientation':ori,**audit})
            print(json.dumps({'tile':name,'sz3_bps':8*sb/X.size,'target_bps':audit['strict_2x_target_bps'],'first_actual_k':audit['first_free_modes_crossing_actual_bytes'],'first_entropy_k':audit['first_free_modes_crossing_zero_order_entropy'],'selected':[{x:r[x] for x in ('free_modes','charged_bps','innovation_zero_order_entropy_bps','residual_energy_fraction_left','crosses_2x_target')} for r in rr if r['free_modes'] in (0,8,16,32,64,96,112,120,124,126,127,128)]},indent=2),flush=True)
        aggregate=[]
        for k in KS:
            rr=[r for r in allrows if r['free_modes']==k]
            b=sum(r['charged_bytes'] for r in rr);sz=sum(r['sz3_bytes'] for r in rr);n=sum(m.C*m.T for _ in rr)
            aggregate.append({'free_modes':k,'charged_bytes':b,'sz3_bytes':sz,'charged_bps':8*b/n,'gain_vs_sz3':sz/b,'strict_2x_target_bytes':sz/2.0,'crosses_2x_target':bool(b<=sz/2.0),'mean_free_mode_energy_fraction':float(np.mean([r['free_mode_energy_fraction'] for r in rr])),'max_ratio_to_2x_target':max(r['ratio_to_strict_2x_target'] for r in rr),'min_tile_gain_vs_sz3':min(r['gain_vs_sz3'] for r in rr)})
        first_agg=next((r for r in aggregate if r['crosses_2x_target']),None)
        out={'global_std':std,'eps':eps,'step':m.STEP,'order':ORDER,'free_mode_counts':list(KS),'tiles':tiles,'aggregate':aggregate,'first_aggregate_free_modes_crossing_2x':None if first_agg is None else first_agg['free_modes'],'rows':allrows,'scope':'Deliberately impossible oracle giveaway test, NOT a compression claim. Each tile gets a locally fitted AR16 predictor for free: model coefficients/predictor state cost zero. The exact residual SVD basis and the first k mode coefficients/reconstruction Ck also cost zero. Only the remaining residual N=E-Ck is mapped to K=round(N/256) and charged through the existing exact self-decoding innovation frame. Decoder reconstruction P+Ck+256K is hard-error verified. This overwhelmingly favors the low-rank hypothesis. The reported first k crossing asks how many of 128 spatial modes would have to be magically free before the remaining actually serialized innovation bytes fall below half of matched SZ3. If dozens of modes are required even under this oracle, better low-rank coding cannot plausibly explain the missing 2x by itself.'}
        print(json.dumps({'first_aggregate_free_modes_crossing_2x':out['first_aggregate_free_modes_crossing_2x'],'aggregate':aggregate},indent=2),flush=True)
        json.dump(out,open('imperial_oracle_free_residual_modes.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
