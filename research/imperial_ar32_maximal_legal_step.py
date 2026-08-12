import json,sys
import h5py,numpy as np
from numba import njit
import imperial_decoder_phase_automaton as c
import imperial_dyadic_shared_resonator as ar

C=128;P=32;TRAIN=1024;NT=8192;TB=1024
STEPS=tuple(range(256,268))
SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))

@njit(cache=True)
def recur(X,co,p,step):
    nc,nt=X.shape;R=np.zeros((nc,nt),np.int32);K=np.zeros((nc,nt),np.int32)
    for cc in range(nc):
        for t in range(nt):
            v=0.0
            if t>=p:
                v=float(co[p])
                for j in range(p):v+=float(co[j])*float(R[cc,t-1-j])
            pred=int(np.rint(v));k=int(np.rint((X[cc,t]-pred)/step));R[cc,t]=pred+step*k;K[cc,t]=k
    return R,K

@njit(cache=True)
def decode(K,co,p,step):
    nc,nt=K.shape;R=np.zeros((nc,nt),np.int32)
    for cc in range(nc):
        for t in range(nt):
            v=0.0
            if t>=p:
                v=float(co[p])
                for j in range(p):v+=float(co[j])*float(R[cc,t-1-j])
            R[cc,t]=int(np.rint(v))+step*int(K[cc,t])
    return R

def encode_frames(K):
    total=0;Kd=np.empty_like(K);reps={}
    for t0 in range(0,NT,TB):
        t1=min(NT,t0+TB);fr=c.encode_k(K[:,t0:t1]);total+=int(fr[0])+20;Kd[:,t0:t1]=fr[2];reps[fr[1]]=reps.get(fr[1],0)+1
    return total,Kd,reps

def matched_sz3(X,eps):
    total=0
    for t0 in range(0,NT,TB):
        t1=min(NT,t0+TB);b,_=c.szrun(X[:,t0:t1],eps);total+=b
    return int(total)

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=c.stats(d);eps=.1*std;rows=[];regions=[]
        for name,c0 in SPECS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T;co=ar.fit_shared(X[:,:TRAIN],P);mb,cd=ar.model_frame(co);szb=matched_sz3(X,eps);regions.append({'region':name,'c0':c0,'samples':int(X.size),'sz3_bytes':szb,'model_bytes':int(mb)})
            for step in STEPS:
                if step/2.0>eps:continue
                R,K=recur(X,np.asarray(cd,np.float32),P,step);me=float(np.max(np.abs(X-R.astype(np.float64))))
                if me>eps*(1+1e-12) or me>step/2.0+1e-9:raise RuntimeError(('construction hard',name,step,me,eps))
                ib,Kd,reps=encode_frames(K);Rd=decode(Kd.astype(np.int32),np.asarray(cd,np.float32),P,step)
                if not np.array_equal(Rd,R):raise RuntimeError(('decode mismatch',name,step))
                fme=float(np.max(np.abs(X-Rd.astype(np.float64))))
                if fme>eps*(1+1e-12):raise RuntimeError(('final hard',name,step,fme,eps))
                total=int(mb)+ib+32;row={'region':name,'c0':c0,'step':step,'bytes':total,'innovation_bytes':ib,'model_bytes':int(mb),'bps':8*total/X.size,'sz3_bytes':szb,'gain_vs_sz3':szb/total,'maxerr':fme,'k_zero_fraction':float(np.mean(K==0)),'k_abs1_fraction':float(np.mean(np.abs(K)==1)),'k_std':float(K.std()),'reps':reps};rows.append(row);print(json.dumps({k:v for k,v in row.items() if k!='reps'}),flush=True)
    n=sum(r['samples'] for r in regions);sz=sum(r['sz3_bytes'] for r in regions);combos=[]
    for step in STEPS:
        rr=[r for r in rows if r['step']==step]
        if not rr:continue
        b=sum(r['bytes'] for r in rr);ib=sum(r['innovation_bytes'] for r in rr);combos.append({'step':step,'bytes':b,'innovation_bytes':ib,'bps':8*b/n,'innovation_bps':8*ib/n,'sz3_bytes':sz,'gain_vs_sz3':sz/b,'maxerr':max(r['maxerr'] for r in rr),'min_region_gain_vs_sz3':min(r['gain_vs_sz3'] for r in rr),'median_k_zero_fraction':float(np.median([r['k_zero_fraction'] for r in rr]))})
    combos.sort(key=lambda z:z['bytes']);base=next(z for z in combos if z['step']==256)
    for z in combos:z['gain_vs_step256']=base['bytes']/z['bytes'];z['innovation_gain_vs_step256']=base['innovation_bytes']/z['innovation_bytes']
    out={'global_std':std,'eps':eps,'ar_order':P,'training_samples':TRAIN,'processed_samples':NT,'width':C,'steps':list(STEPS),'regions':[x[0] for x in SPECS],'aggregate':combos,'region_metadata':regions,'rows':rows,
         'scope':'Exact persistent-AR32 lattice-spacing sweep. One shared float32 AR32+intercept is fit only from the first 1024 source samples of each fixed hard/easy/medium/far 128-channel region. The same model is reused for every integer reconstruction spacing 256..267; each step recursively generates its own decoder state and exact integer K field through t<8192. Every K frame uses the existing self-decoding encode_k backend, is byte-decoded, and the complete trajectory is regenerated. Only steps with step/2 <= unchanged public epsilon are legal; final max error is independently verified. Model/framing bytes are fully charged and matched SZ3 uses the identical 128x1024 partition. Purpose: test whether the binary-friendly step=256 incumbent is leaving legal distortion/rate on the table. No AI; four-region 8192-sample gate, not whole-array.'}
    print(json.dumps({'aggregate':combos},indent=2),flush=True);json.dump(out,open('imperial_ar32_maximal_legal_step.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
