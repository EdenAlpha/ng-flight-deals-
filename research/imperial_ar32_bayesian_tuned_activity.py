import json,sys
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as a
import imperial_ar32_bayesian_context_mixer as m

C=128;NT=8192;TB=1024
REGIONS=(("hard",512,4),("easy",2304,64))
CONTROL_W=8

def run_mix(K,W):
    m.W=int(W);m.NT=NT
    return m.arithmetic_mix(K)

def main(path):
    a.NT=NT;m.NT=NT
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd;rows=[]
        for region,c0,tuned_w in REGIONS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,hu=a.fits(X);R,K=a.run_ar(X,hu)
            base,_,_,Kbd=a.arithmetic(K)
            if not np.array_equal(a.decode_source(Kbd,hu),R):raise RuntimeError((region,'base replay'))
            candidates=[]
            for W in (CONTROL_W,tuned_w):
                n,bits,nb,Kd,w=run_mix(K,W);Rd=a.decode_source(Kd,hu);me=float(np.max(np.abs(X-Rd.astype(np.float64))))
                if not np.array_equal(Rd,R):raise RuntimeError((region,W,'source replay'))
                if me>eps*(1+1e-12):raise RuntimeError((region,W,'hard',me,eps))
                candidates.append({'activity_window':int(W),'bytes':int(n),'bps':8*n/X.size,'gain_vs_baseline':base/n,'arithmetic_bits':int(bits),'symbol_bits':int(nb),'maxerr':me,'final_expert_weights':w.tolist()})
            sz=0
            for t0 in range(0,NT,TB):z,_=a.m.szrun(X[:,t0:t0+TB],eps);sz+=int(z)
            for q in candidates:q['gain_vs_sz3']=sz/q['bytes']
            control=[q for q in candidates if q['activity_window']==CONTROL_W][0]
            tuned=[q for q in candidates if q['activity_window']==tuned_w][0]
            tuned['gain_vs_w8_mixer']=control['bytes']/tuned['bytes']
            best=min(candidates,key=lambda q:q['bytes'])
            row={'region':region,'c0':c0,'samples':int(X.size),'eps':float(eps),'baseline_bytes':int(base),'baseline_bps':8*base/X.size,'sz3_bytes':int(sz),'sz3_bps':8*sz/X.size,'control_w8':{k:v for k,v in control.items() if k!='final_expert_weights'},'tuned':{k:v for k,v in tuned.items() if k!='final_expert_weights'},'best':{k:v for k,v in best.items() if k!='final_expert_weights'}}
            rows.append(row);print(json.dumps(row,indent=2),flush=True)
        json.dump({'global_std':gstd,'eps':eps,'rows':rows,'scope':'Exact follow-up to PR #450 using the independently measured activity timescales from PR #455. The four-expert Bayesian arithmetic mixer, K reconstruction, expert definitions, training boundary and probability updates are unchanged. Only the rolling activity6 expert window is changed from the old universal W=8 to W=4 on hard and W=64 on easy; W=8 is rerun as an exact control. No new side information is transmitted in this regional gate. Exact arithmetic K decode, bit-identical source replay and unchanged max-error verification are mandatory. No AI. Draft/do not merge.'},open('imperial_ar32_bayesian_tuned_activity.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
