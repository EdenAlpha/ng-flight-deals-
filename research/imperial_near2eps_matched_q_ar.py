import json,sys
import h5py,numpy as np
from numba import njit
import imperial_near_2eps_resonance_sweep as s
import imperial_defect_restricted_rank_address as rr
import imperial_resonant_learned_law_address as g
import imperial_dyadic_shared_resonator as ar
import imperial_decoder_phase_automaton as m

FAC=1.99995
ORDERS=(16,32,64)
PREFIX=256
AR_HEADER=32
OURS_HEADER=48

@njit(cache=True)
def predq(Q,c,t,co,p):
    if t<p:return 0
    v=float(co[-1])
    for j in range(p):v+=float(co[j])*float(Q[c,t-1-j])
    return int(np.rint(v))

@njit(cache=True)
def ar_k(Q,co,p):
    K=np.empty(Q.shape,np.int32)
    R=np.empty(Q.shape,np.int32)
    for c in range(Q.shape[0]):
        for t in range(Q.shape[1]):
            pr=predq(R,c,t,co,p);k=int(Q[c,t])-pr;K[c,t]=k;R[c,t]=pr+k
    return K,R

@njit(cache=True)
def ar_replay(K,co,p):
    R=np.empty(K.shape,np.int32)
    for c in range(K.shape[0]):
        for t in range(K.shape[1]):R[c,t]=predq(R,c,t,co,p)+int(K[c,t])
    return R


def encode_field(A):
    dense=m.encode_k(np.ascontiguousarray(A,np.int32));cands=[(int(dense[0]),'dense_'+dense[1],np.asarray(dense[2],np.int32))]
    rb,rrep,RD,detail=rr.restricted_rank_frame(A);cands.append((int(rb),'restricted_rank',RD));cands.sort(key=lambda x:x[0]);return cands[0],cands


def ar_candidate(Q,X,h,p,train_kind):
    src=Q[:,:PREFIX] if train_kind=='prefix' else Q
    co=ar.fit_shared(src,p);mb,cd=ar.model_frame(co);K,R=ar_k(Q,cd,p)
    if not np.array_equal(R,Q):raise RuntimeError(('encoder Q',p,train_kind))
    best,allrep=encode_field(K);kb,rep,Kd=best;Rd=ar_replay(Kd,cd,p)
    if not np.array_equal(Rd,Q):raise RuntimeError(('AR replay',p,train_kind))
    me=float(np.max(np.abs(X-Rd.astype(np.float64)*h)))
    total=int(mb)+kb+AR_HEADER
    return {'bytes':total,'bps':8*total/X.size,'order':p,'training':train_kind,'model_bytes':int(mb),'innovation_bytes':kb,'rep':rep,'maxerr':me,'k_zero_fraction':float(np.mean(K==0)),'k_std':float(K.std()),'representations':[{'bytes':int(x[0]),'rep':x[1]} for x in allrep]}


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    z=s.build_at(X,eps,FAC,0);ours=s.rank_materialize(X,eps,z,'learned_law');Q=z['Q'];h=z['h']
    if z['mean_legal']!=1.0 or z['max_legal']!=1:raise RuntimeError(('expected unique legal lattice',z['mean_legal'],z['max_legal']))
    # Source reconstruction is intentionally identical for every comparator below.
    source_me=float(np.max(np.abs(X-Q.astype(np.float64)*h)))
    if source_me>eps*(1+5e-6):raise RuntimeError(('source hard',source_me,eps))
    rows=[]
    for p in ORDERS:
        for training in ('prefix','full'):
            r=ar_candidate(Q,X,h,p,training);rows.append(r);print(json.dumps({k:v for k,v in r.items() if k!='representations'}),flush=True)
    rows.sort(key=lambda r:r['bytes']);best=rows[0]
    szb,ori=m.szrun(X,eps)
    ours['gain_vs_matched_ar']=best['bytes']/ours['bytes'];ours['gain_vs_sz3']=szb/ours['bytes']
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'hfac':FAC,'h':h,'unique_legal_state':True,'identical_reconstruction_maxerr':source_me,'ours':ours,'matched_q_ar':rows,'best_matched_q_ar':best,'sz3':{'bytes':int(szb),'orientation':ori},'scope':'Strict same-reconstruction fairness audit. The near-2epsilon factor is fixed at the legal-edge winner h=1.99995epsilon, for which every source sample has exactly one legal Q lattice state. Therefore the learned sparse causal codec and every AR comparator encode the identical Q field and reconstruct exactly the same source values h*Q. The only difference is the causal address model. AR orders 16/32/64 are tested both with the historical prefix-trained model and a deliberately favorable full-target-trained model; every float32 coefficient model is serialized/decoded and charged. Each AR innovation field is allowed the same dense representation menu plus the exact restricted-rank coder, and the smaller real stream wins. AR keeps its historically smaller 32-byte framing allowance versus 48 bytes for the learned-law stream, favoring the comparator. Exact Q replay and unchanged hard source error are mandatory. This isolates predictor/address quality from quantizer-spacing effects.'}
    json.dump(out,open('imperial_near2eps_matched_q_ar.json','w'),indent=2)
    print(json.dumps({'summary':{'ours':ours['bytes'],'matched_ar':best['bytes'],'matched_order':best['order'],'training':best['training'],'gain_vs_matched_ar':best['bytes']/ours['bytes'],'sz3':int(szb),'gain_vs_sz3':szb/ours['bytes'],'maxerr':source_me}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
