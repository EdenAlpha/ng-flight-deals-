import json,sys,hashlib
import h5py,numpy as np
import imperial_decoder_phase_automaton as m
import imperial_dyadic_shared_resonator as r

C=128;TB=1024;T=30000
SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
ORDERS=(16,32)
KINDS=('shared','per_channel')

def fit_model(train,p,kind):
    co=r.fit_shared(train,p) if kind=='shared' else r.fit_per_channel(train,p)
    mb,cd=r.model_frame(co)
    digest=hashlib.sha256(np.ascontiguousarray(cd,np.float32).tobytes()).hexdigest()
    return mb,cd,digest

def predict_block(R,t,cd,p,kind):
    if t<p:return np.zeros(R.shape[0],np.int64)
    if kind=='shared':
        v=np.full(R.shape[0],float(cd[-1]),np.float64)
        for j in range(p):v+=float(cd[j])*R[:,t-1-j]
    else:
        v=np.asarray(cd[:,-1],np.float64).copy()
        for j in range(p):v+=np.asarray(cd[:,j],np.float64)*R[:,t-1-j]
    if not np.all(np.isfinite(v)):raise RuntimeError(('nonfinite',t,p,kind))
    return np.rint(np.clip(v,-2.0e9,2.0e9)).astype(np.int64)

def build_k(X,cd,p,kind):
    nc,nt=X.shape;R=np.zeros((nc,nt),np.int64);K=np.zeros((nc,nt),np.int64)
    for t in range(nt):
        pred=predict_block(R,t,cd,p,kind)
        k=np.rint((X[:,t]-pred)/m.STEP).astype(np.int64)
        R[:,t]=pred+m.STEP*k;K[:,t]=k
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>128.000001:raise RuntimeError(('construction hard error',p,kind,me))
    return R,K,me

def decode_k(K,cd,p,kind):
    nc,nt=K.shape;R=np.zeros((nc,nt),np.int64)
    for t in range(nt):
        pred=predict_block(R,t,cd,p,kind);R[:,t]=pred+m.STEP*K[:,t]
    return R

def encode_full(X,eps,p,kind):
    train=X[:,:TB];mb,cd,digest=fit_model(train,p,kind);R,K,me=build_k(X,cd,p,kind)
    Kd=np.empty_like(K);innov=0;frames=[]
    for fi,t0 in enumerate(range(0,T,TB)):
        t1=min(T,t0+TB);fr=m.encode_k(K[:,t0:t1]);ib=int(fr[0])+20;innov+=ib;Kd[:,t0:t1]=fr[2]
        frames.append({'frame':fi,'t0':t0,'ns':t1-t0,'bytes':ib,'rep':fr[1]})
    Rd=decode_k(Kd,cd,p,kind)
    if not np.array_equal(Rd,R):raise RuntimeError(('decoder mismatch',p,kind))
    final_me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if final_me>eps*(1+1e-12) or final_me>128.000001:raise RuntimeError(('final hard error',p,kind,final_me,eps))
    total=int(mb+innov+32)
    co=np.asarray(cd,np.float32)
    return {'kind':kind,'order':p,'bytes':total,'bps':8*total/X.size,'model_bytes':int(mb),'model_bps':8*mb/X.size,'innovation_bytes':int(innov),'innovation_bps':8*innov/X.size,
            'model_sha256':digest,'maxerr':final_me,'k_zero_fraction':float(np.mean(K==0)),'k_abs1_fraction':float(np.mean(np.abs(K)==1)),'k_std':float(K.std()),
            'median_ar1':float(np.median(co[:,0])) if kind=='per_channel' else None,'ar1_iqr':float(np.percentile(co[:,0],75)-np.percentile(co[:,0],25)) if kind=='per_channel' else None,
            'coefficient_spread_l2':float(np.mean(np.std(co[:,:-1],axis=0))) if kind=='per_channel' else None,'frames':frames}

def matched_sz3(X,eps):
    total=0;rows=[]
    for fi,t0 in enumerate(range(0,T,TB)):
        t1=min(T,t0+TB);sb,ori=m.szrun(X[:,t0:t1],eps);total+=sb;rows.append({'frame':fi,'t0':t0,'ns':t1-t0,'bytes':sb,'orientation':ori})
    return int(total),rows

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;rows=[];regions=[]
        if tuple(d.shape)!=(30000,6912):raise RuntimeError(('shape',d.shape))
        for name,c0 in SPECS:
            X=np.asarray(d[:,c0:c0+C],np.float64).T;szb,szframes=matched_sz3(X,eps);reg={'region':name,'c0':c0,'samples':int(X.size),'local_std':float(X.std()),'sz3_bytes':szb,'sz3_bps':8*szb/X.size,'sz3_frames':szframes};regions.append(reg)
            for p in ORDERS:
                for kind in KINDS:
                    z=encode_full(X,eps,p,kind);z.update({'region':name,'c0':c0,'sz3_bytes':szb,'gain_vs_sz3':szb/z['bytes'],'local_std':reg['local_std'],'eps_over_local_std':float(eps/reg['local_std'])});rows.append(z)
                    print(json.dumps({k:v for k,v in z.items() if k!='frames'},indent=2),flush=True)
        n=sum(x['samples'] for x in regions);sz=sum(x['sz3_bytes'] for x in regions);combos=[]
        for p in ORDERS:
            for kind in KINDS:
                rr=[x for x in rows if x['order']==p and x['kind']==kind];b=sum(x['bytes'] for x in rr);ib=sum(x['innovation_bytes'] for x in rr);mb=sum(x['model_bytes'] for x in rr)
                combos.append({'order':p,'kind':kind,'bytes':b,'innovation_bytes':ib,'model_bytes':mb,'bps':8*b/n,'innovation_bps':8*ib/n,'model_bps':8*mb/n,'sz3_bytes':sz,'gain_vs_sz3':sz/b,
                               'min_region_gain_vs_sz3':min(x['gain_vs_sz3'] for x in rr),'median_region_gain_vs_sz3':float(np.median([x['gain_vs_sz3'] for x in rr])),'median_k_zero_fraction':float(np.median([x['k_zero_fraction'] for x in rr]))})
        combos.sort(key=lambda x:x['bytes'])
        base=next(x for x in combos if x['order']==16 and x['kind']=='shared')
        for x in combos:x['gain_vs_shared_p16']=base['bytes']/x['bytes'];x['innovation_gain_vs_shared_p16']=base['innovation_bytes']/x['innovation_bytes']
        out={'global_std':std,'eps':eps,'step':m.STEP,'training_samples':TB,'time_samples':T,'width':C,'regions':[x[0] for x in SPECS],'orders':list(ORDERS),'kinds':list(KINDS),'aggregate':combos,'region_metadata':regions,'rows':rows,
             'scope':'Persistent per-sensor dynamical-law screen. For each fixed 128-channel hard/easy/medium/far Imperial block, shared or per-channel float32 AR(p)+intercept coefficients are fit ONLY from the first 1024 source samples and serialized/byte-decoded once. That identical model is then frozen across all 30000 times with continuous recursive state; only exact 256-step innovations are transmitted in 1024-sample self-decoding frames. All model/framing bytes are charged once, every K frame is byte-decoded, the complete 30k trajectory is regenerated from decoded model+K, and max error <=128 is verified under the unchanged global 10%-std epsilon. p16 and p32 are compared with matched SZ3 on the identical 128x1024 partition. This directly tests whether the old 1024-sample per-channel loss was merely model-overhead amortization. No AI; four full-minute region screen, not yet whole-array.'}
        print(json.dumps({'aggregate':combos},indent=2),flush=True);json.dump(out,open('imperial_persistent_perchannel_ar.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
