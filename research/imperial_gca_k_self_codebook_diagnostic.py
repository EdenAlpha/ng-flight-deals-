import json,math,sys
import h5py,numpy as np
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as ah
import imperial_huber_ar32_component_zsm_gps as cg
import imperial_gca_residue_codebook as rc

C=128;NT=30000;C0=512;STEP=267;RAD=133
PHASES=np.array([-133,-96,-64,-32,0,32,64,96,133],np.int16)
FAMS=('current','cur_prev_next','cur_left_right','cur_next_right')

def clip4a(K): return np.clip(K,-4,4).astype(np.int16)+4

def ctx(K,fam):
    Q=clip4a(K).astype(np.int32)
    if fam=='current': return Q
    if fam=='cur_prev_next':
        prev=np.full_like(Q,4);prev[:,1:]=Q[:,:-1]
        nex=np.full_like(Q,4);nex[:,:-1]=Q[:,1:]
        return (Q*9+prev)*9+nex
    if fam=='cur_left_right':
        left=np.full_like(Q,4);left[1:]=Q[:-1]
        right=np.full_like(Q,4);right[:-1]=Q[1:]
        return (Q*9+left)*9+right
    nex=np.full_like(Q,4);nex[:,:-1]=Q[:,1:]
    right=np.full_like(Q,4);right[:-1]=Q[1:]
    return (Q*9+nex)*9+right

def nctx(fam): return 9 if fam=='current' else 729

def proxy_vec(k):
    a=np.abs(k.astype(np.int64));q=np.zeros_like(a)
    z=a>0;q[z]=np.floor(np.log2(a[z])).astype(np.int64)
    return 1.0+z.astype(np.float64)*(2.0+2.0*q)

def fit_table(N,K,fam,min_count=64):
    G=ctx(K,fam).reshape(-1);V=N.reshape(-1);tab=np.zeros(nctx(fam),np.int16);counts=np.bincount(G,minlength=nctx(fam))
    for g in np.flatnonzero(counts>=min_count):
        idx=np.flatnonzero(G==g)
        if len(idx)>20000: idx=idx[np.linspace(0,len(idx)-1,20000,dtype=np.int64)]
        v=V[idx];best=(1e300,0)
        for d in PHASES:
            kk=np.floor_divide(v-int(d)+RAD,STEP);s=float(proxy_vec(kk).sum())
            if s<best[0]:best=(s,int(d))
        tab[g]=best[1]
    return tab,counts

def apply(N,K,fam,tab):
    G=ctx(K,fam);D=tab[G].astype(np.int64);return np.floor_divide(N-D+RAD,STEP).astype(np.int32),D

def h0(a):
    _,n=np.unique(a,return_counts=True);p=n/n.sum();return float(-(p*np.log2(p)).sum())

def main(path):
    with h5py.File(path,'r') as hf:
        d=hf['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,C0:C0+C],np.float64).T
    _,co=ah.fits(X);model,cod=cg.model_frame(co);R0,K0=ah.run_ar(X,cod);P0=R0.astype(np.int64)-STEP*K0.astype(np.int64);Xi=np.rint(X).astype(np.int64);N=Xi-P0
    base_proxy=rc.k_proxy(K0);base_h0=h0(K0);rows=[]
    for fam in FAMS:
        K=K0.copy();history=[];tab=np.zeros(nctx(fam),np.int16);seen={}
        for it in range(6):
            tab,counts=fit_table(N,K,fam);Kn,D=apply(N,K,fam,tab);chg=int(np.sum(Kn!=K));key=hash(Kn.tobytes())
            row={'iter':it,'proxy_bps':rc.k_proxy(Kn),'h0_bps':h0(Kn),'changed_from_prev':chg,'changed_from_baseline':int(np.sum(Kn!=K0)),'nonzero_phases':int(np.count_nonzero(tab)),'side_bytes_raw':int(2*len(tab))}
            history.append(row);print(json.dumps({'iter':{'family':fam,**row}}),flush=True)
            if np.array_equal(Kn,K):K=Kn;break
            if key in seen:K=Kn;break
            seen[key]=it;K=Kn
        # Fixed-point consistency under its own final context and table.
        Kcheck,D=apply(N,K,fam,tab);cons=float(np.mean(Kcheck==K));
        rows.append({'family':fam,'final_proxy_bps':rc.k_proxy(K),'final_h0_bps':h0(K),'proxy_gain_bps':base_proxy-rc.k_proxy(K),'proxy_gain_bytes_equiv':(base_proxy-rc.k_proxy(K))*K.size/8.0,'h0_gain_bps':base_h0-h0(K),'changed_from_baseline':int(np.sum(K!=K0)),'fixed_point_consistency':cons,'side_bytes_raw':int(2*len(tab)),'nonzero_phases':int(np.count_nonzero(tab)),'history':history})
    rows.sort(key=lambda z:z['final_proxy_bps']);out={'shape':[C,NT],'eps':eps,'baseline_proxy_bps':base_proxy,'baseline_k_h0_bps':base_h0,'phase_menu':[int(x) for x in PHASES],'rows':rows,'best':rows[0],'scope':'Diagnostic only. Baseline Huber-AR32 predictor is frozen, then a phase table is iteratively conditioned on the K field itself, including noncausal next/right K contexts. The test asks whether already-decoded K can predict useful legal lattice-phase choices. It reports fixed-point consistency under the frozen predictor, proxy/H0 gains and raw table cost. It is NOT an exact codec because changing reconstruction phases would change the recursive AR32 predictor; any promising family must next be solved recursively and physically encoded/decoded.'};json.dump(out,open('imperial_gca_k_self_codebook_diagnostic.json','w'),indent=2);print(json.dumps({'summary':{'baseline_proxy':base_proxy,'baseline_h0':base_h0,'best':rows[0]}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
