import json,sys
import h5py,numpy as np
import imperial_rank_motion_coordinate as m

C=m.C;T=m.T;STEP=m.STEP
MODES=('time1','time2','ar8_prefix256')

def fit_ar8(Q,n=256):
    o=8;ys=[];xs=[]
    for t in range(o,n):
        ys.append(Q[:,t].astype(np.float64));xs.append(np.stack([Q[:,t-1-j] for j in range(o)],axis=1).astype(np.float64))
    y=np.concatenate(ys);A=np.concatenate(xs,axis=0);D=np.column_stack([np.ones(A.shape[0]),A]);ridge=1e-6*np.eye(D.shape[1]);ridge[0,0]=0
    return np.linalg.solve(D.T@D+ridge,D.T@y).astype(np.float32)

def predictor(Q,t,mode,beta=None):
    if mode=='time1':return Q[:,t-1].astype(np.float64)
    if mode=='time2':return (2*Q[:,t-1]-Q[:,t-2]).astype(np.float64)
    if mode=='ar8_prefix256':
        p=np.full(C,float(beta[0]),np.float64)
        for j,a in enumerate(beta[1:]):p+=float(a)*Q[:,t-1-j]
        return p
    raise ValueError(mode)

def build_transport(Q,mode):
    start=1 if mode=='time1' else (2 if mode=='time2' else 256);beta=fit_ar8(Q,start) if mode=='ar8_prefix256' else None
    n=T-start;S=np.empty((C,n),np.int64);E=np.empty((C,n),np.int64);DP=np.empty((C,n),np.int64);disp=[];same=[]
    for jj,t in enumerate(range(start,T)):
        p=predictor(Q,t,mode,beta);order=np.argsort(p,kind='stable');rpred=np.empty(C,np.int64);rpred[order]=np.arange(C,dtype=np.int64)
        s=np.sort(Q[:,t],kind='stable');S[:,jj]=s;qpred=s[rpred];E[:,jj]=Q[:,t]-qpred
        pos=np.empty(C,np.int64)
        vals=np.unique(Q[:,t])
        for v in vals:
            ch=np.flatnonzero(Q[:,t]==v);slots=np.flatnonzero(s==v);ch=ch[np.argsort(rpred[ch],kind='stable')];pos[ch]=slots
        if not np.array_equal(s[pos],Q[:,t]):raise RuntimeError(('position assignment',mode,t))
        DP[:,jj]=pos-rpred;disp.append(float(np.mean(np.abs(DP[:,jj]))));same.append(float(np.mean(DP[:,jj]==0)))
    model_bytes=0 if beta is None else 32+4*len(beta)
    return start,beta,S,E,DP,model_bytes,{'mean_abs_rank_defect':float(np.mean(disp)),'median_abs_rank_defect':float(np.median(disp)),'rank_exact_fraction':float(np.mean(same))}

def decode_check(seed,S,D,mode,beta,kind,Q):
    R=np.empty_like(Q);start=seed.shape[1];R[:,:start]=seed
    for jj,t in enumerate(range(start,T)):
        p=predictor(R,t,mode,beta);order=np.argsort(p,kind='stable');rpred=np.empty(C,np.int64);rpred[order]=np.arange(C,dtype=np.int64);s=S[:,jj]
        if kind=='numeric':R[:,t]=s[rpred]+D[:,jj]
        else:
            pos=rpred+D[:,jj]
            if np.any(pos<0)|np.any(pos>=C):raise RuntimeError(('position range',mode,t))
            R[:,t]=s[pos]
    if not np.array_equal(R,Q):raise RuntimeError(('transport decode mismatch',mode,kind))

def encode_mode(Q,mode):
    start,beta,S,E,DP,model_bytes,st=build_transport(Q,mode);seed=Q[:,:start].copy();seedb,seedr=m.encode_array(seed);sb,sr=m.encode_array(S);eb,er=m.encode_array(E);pb,pr=m.encode_array(DP)
    cands=[]
    for kind,b,rep,D in (('numeric',eb,er,E),('position',pb,pr,DP)):
        decode_check(seed,S,D,mode,beta,kind,Q);total=seedb+sb+b+model_bytes+64
        cands.append({'kind':kind,'bytes':total,'seed_bytes':seedb,'seed_rep':seedr,'sorted_bytes':sb,'sorted_rep':sr,'defect_bytes':b,'defect_rep':rep,'model_bytes':model_bytes})
    best=min(cands,key=lambda x:x['bytes']);best.update(st);best['mode']=mode;best['start']=start;best['coefficients']=None if beta is None else [float(x) for x in beta];return best,cands

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;rows=[];tiles=[]
        for name,t0,c0 in m.SPECS:
            X=np.asarray(d[t0:t0+T,c0:c0+C],np.float64).T;Q=np.rint(X/STEP).astype(np.int64);me=float(np.max(np.abs(X-Q*STEP)))
            if me>128.000001 or me>eps:raise RuntimeError(('grid',name,me,eps))
            szb,ori=m.szrun(X,eps);fb,fr=m.encode_array(Q);tiles.append({'tile':name,'sz3_bytes':szb,'fixed256_bytes':fb,'fixed256_rep':fr})
            for mode in MODES:
                best,cands=encode_mode(Q,mode);maxerr=float(np.max(np.abs(X-Q*STEP)));best.update({'tile':name,'bps':8*best['bytes']/Q.size,'sorted_bps':8*best['sorted_bytes']/Q.size,'defect_bps':8*best['defect_bytes']/Q.size,'seed_bps':8*best['seed_bytes']/Q.size,'sz3_bytes':szb,'fixed256_bytes':fb,'gain_vs_sz3':szb/best['bytes'],'gain_vs_fixed256':fb/best['bytes'],'maxerr':maxerr,'candidates':cands});rows.append(best);print(json.dumps({k:v for k,v in best.items() if k not in ('candidates','coefficients')}),flush=True)
        n=C*T*len(tiles);szb=sum(x['sz3_bytes'] for x in tiles);fb=sum(x['fixed256_bytes'] for x in tiles);combos=[]
        for mode in MODES:
            rr=[r for r in rows if r['mode']==mode];b=sum(r['bytes'] for r in rr)
            combos.append({'mode':mode,'bytes':b,'bps':8*b/n,'gain_vs_sz3':szb/b,'gain_vs_fixed256':fb/b,'sorted_bps':8*sum(r['sorted_bytes'] for r in rr)/n,'defect_bps':8*sum(r['defect_bytes'] for r in rr)/n,'seed_model_bps':8*sum(r['seed_bytes']+r['model_bytes']+64 for r in rr)/n,'median_abs_rank_defect':float(np.median([r['median_abs_rank_defect'] for r in rr])),'median_rank_exact_fraction':float(np.median([r['rank_exact_fraction'] for r in rr])),'selected_kinds':[r['kind'] for r in rr],'min_tile_gain_vs_sz3':min(r['gain_vs_sz3'] for r in rr)})
        combos.sort(key=lambda x:x['bytes']);out={'std':std,'eps':eps,'step':STEP,'patch_shape':[C,T],'modes':list(MODES),'tiles':tiles,'combos':combos,'rows':rows,'scope':'Collective predictive optimal-transport assignment screen. The current 128-channel 256-grid amplitude multiset is transmitted in sorted form. Before seeing current sensor assignments, the decoder ranks sensors by a causal predictor from already-decoded history (time1, time2, or a charged AR8 model fitted/transmitted from the first 256 samples). Sorted current amplitudes are monotonically transported onto that predicted sensor order at zero assignment cost. Encoder then transmits only either numeric defects from this collective assignment or exact position/rank defects, with tie slots assigned to minimize rank displacement. Seed, sorted multiset, model and defects are all self-decoding/charged; exact Q is regenerated before the <=128 hard-error check. This tests whether sensor identity is mostly predictable ordering even when amplitude residuals are large. Matched SZ3/fixed256 rerun; no AI; four-tile screen.'}
        print(json.dumps({'combos':combos},indent=2));json.dump(out,open('imperial_predictive_transport_assignment.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
