import sys,math,numpy as np
import imperial_ar32_volatility_state_code as q


def entropy(vals):
    x=np.asarray(vals).ravel()
    if x.size==0:return 0.0
    _,cnt=np.unique(x,return_counts=True);p=cnt.astype(np.float64)/cnt.sum()
    return float(-(p*np.log2(p)).sum())

_old=q.evaluate

def evaluate_oracle(K,G,B):
    out=_old(K,G,B)
    nc,nt=K.shape;held=nt-q.TRAIN
    uncond_bits=0.0;cond_bits=0.0;state_bits=0
    details=[]
    for c0 in range(0,nc,G):
        A=K[c0:c0+G]
        trscale=np.sqrt(np.mean(A[:,:q.TRAIN].astype(np.float64)**2,axis=0))
        tesca=np.sqrt(np.mean(A[:,q.TRAIN:].astype(np.float64)**2,axis=0))
        th=q.state_thresholds(trscale,B);se=q.states(tesca,th);H0=entropy(A[:,q.TRAIN:]);uncond_bits+=H0*G*held
        hs=[]
        for s in range(B):
            mask=se==s;n=int(mask.sum())
            h=entropy(A[:,q.TRAIN:][:,mask]) if n else 0.0
            cond_bits+=h*G*n;hs.append({'state':s,'times':n,'entropy_bps':h})
        sb=int(math.ceil(math.log2(B)))*held;state_bits+=sb
        details.append({'c0':c0,'unconditioned_entropy_bps':H0,'state_entropies':hs,'raw_state_bits':sb})
    ns=nc*held
    out['oracle_empirical_unconditioned_bps']=uncond_bits/ns
    out['oracle_empirical_conditioned_symbol_bps']=cond_bits/ns
    out['oracle_empirical_conditioned_plus_raw_state_bps']=(cond_bits+state_bits)/ns
    out['oracle_empirical_net_saving_bps']=(uncond_bits-cond_bits-state_bits)/ns
    out['oracle_empirical_details']=details
    return out

q.evaluate=evaluate_oracle

if __name__=='__main__':q.main(sys.argv[1])
