import json,sys
import h5py,numpy as np
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

C0S=(512,544,576,608)
T0=29696
NT=304


def ar32_variable(X,eps):
    X=np.asarray(X,np.float64);C,nt=X.shape
    if C!=g.C:raise RuntimeError(('channels',C))
    train=min(g.TRAIN,nt)
    co=g.ar.fit_shared(X[:,:train],g.P)
    mb,cd=g.ar.model_frame(co)
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for c in range(C):
        for t in range(nt):
            pred=g.ar.predict_hist(R,c,t,cd,g.P,'shared')
            k=int(np.rint((float(X[c,t])-pred)/g.AR_STEP))
            R[c,t]=pred+g.AR_STEP*k;K[c,t]=k
    kb,kr,Kd=g.frame(K);Rd=np.zeros_like(R)
    for c in range(C):
        for t in range(nt):
            Rd[c,t]=g.ar.predict_hist(Rd,c,t,cd,g.P,'shared')+g.AR_STEP*int(Kd[c,t])
    if not np.array_equal(Rd,R):raise RuntimeError('tail ar replay')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('tail ar hard',me,eps))
    total=int(mb)+int(kb)+32
    return {'bytes':total,'model_bytes':int(mb),'innovation_bytes':int(kb),'rep':kr,'maxerr':me,'bps':8*total/X.size}


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std
        rows=[];ar_total=sz_total=0
        for c0 in C0S:
            X=np.asarray(d[T0:T0+NT,c0:c0+g.C],np.float64).T
            if X.shape!=(g.C,NT):raise RuntimeError(('shape',c0,X.shape))
            ar=ar32_variable(X,eps);sz,ori=m.szrun(X,eps)
            rec={'c0':int(c0),'t0':T0,'nt':NT,'fallback_bytes':int(ar['bytes']),'ar32':int(ar['bytes']),'sz3':int(sz),'gain_sz3':int(sz)/int(ar['bytes']),'maxerr':float(ar['maxerr'])}
            rows.append(rec);ar_total+=int(ar['bytes']);sz_total+=int(sz);print(json.dumps(rec),flush=True)
        agg={'fallback_ours':ar_total,'ar32':ar_total,'sz3':sz_total,'gain_sz3':sz_total/ar_total,'samples':len(C0S)*g.C*NT,'tiles':len(C0S)}
        out={'eps':eps,'cases':rows,'aggregate':agg,'scope':'Exact final 304-sample tail for channels 512:640. The portfolio intentionally falls back to the incumbent charged AR32 step267 codec. This helper is the same shared-AR32 model/innovation/replay contract generalized from fixed 1024 loops to nt=304. Ours therefore equals AR32 exactly on this tail; SZ3 is rerun on the same four 32x304 objects. This tail can be added disjointly to PR572 0:29696 totals for a literal full 128x30000 hard-region accounting.'}
        json.dump(out,open('imperial_hard_tail_304.json','w'),indent=2);print(json.dumps({'summary':agg},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
