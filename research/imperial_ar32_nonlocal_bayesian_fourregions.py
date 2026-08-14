import json,sys
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as a
import imperial_ar32_nonlocal_residual_stencil as s
import imperial_ar32_bayesian_context_mixer as m

C=128;NT=8192;TB=1024
REGIONS=(('hard',512),('easy',2304),('medium',4352),('far',6400))

def main(path):
    a.NT=NT;s.NT=NT;m.NT=NT
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd;rows=[]
        for region,c0 in REGIONS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,hu=a.fits(X);Rb,Kb=a.run_ar(X,hu)
            base,_,_,Kbd=a.arithmetic(Kb);base_mix,_,_,Kbm,_=m.arithmetic_mix(Kb)
            if not np.array_equal(a.decode_source(Kbd,hu),Rb) or not np.array_equal(a.decode_source(Kbm,hu),Rb):raise RuntimeError((region,'baseline replay'))
            models=s.fit_models(X,Rb,Kb);screen=[]
            for ids,co,trmse in models:
                extra=18+5*len(ids)
                for strength in s.STRENGTHS:
                    R,K=s.run_model(X,hu,ids,co,strength);me=float(np.max(np.abs(X-R.astype(np.float64))))
                    if me>eps*(1+1e-12):raise RuntimeError((region,'hard',len(ids),strength,me,eps))
                    bb=s.backend(K,extra);screen.append((bb,ids,co,trmse,strength,R,K,extra))
            screen.sort(key=lambda x:x[0]);_,ids,co,trmse,strength,R,K,extra=screen[0]
            normal,_,_,Knd=a.arithmetic(K);normal+=extra
            mixed,bits,nb,Kmd,_=m.arithmetic_mix(K);mixed+=extra
            Rn=s.decode_model(Knd,hu,ids,co,strength);Rm=s.decode_model(Kmd,hu,ids,co,strength)
            if not np.array_equal(Rn,R) or not np.array_equal(Rm,R):raise RuntimeError((region,'stack replay'))
            me=float(np.max(np.abs(X-Rm.astype(np.float64))))
            if me>eps*(1+1e-12):raise RuntimeError((region,'stack hard',me,eps))
            sz=0
            for t0 in range(0,NT,TB):z,_=a.m.szrun(X[:,t0:t0+TB],eps);sz+=int(z)
            row={'region':region,'c0':c0,'samples':int(X.size),'sz3_bytes':sz,'sz3_bps':8*sz/X.size,'baseline_bytes':int(base),'baseline_bps':8*base/X.size,'baseline_mixer_bytes':int(base_mix),'baseline_mixer_bps':8*base_mix/X.size,'nonlocal_normal_bytes':int(normal),'nonlocal_normal_bps':8*normal/X.size,'nonlocal_mixer_bytes':int(mixed),'nonlocal_mixer_bps':8*mixed/X.size,'gain_stack_vs_baseline':base/mixed,'gain_stack_vs_baseline_mixer':base_mix/mixed,'gain_stack_vs_nonlocal_normal':normal/mixed,'gain_stack_vs_sz3':sz/mixed,'taps':int(len(ids)),'strength':float(strength),'tap_ids':[int(i) for i in ids],'tap_offsets':[list(s.BANK[int(i)]) for i in ids],'train_rmse_k':float(trmse),'k_zero_fraction':float(np.mean(K==0)),'k_std':float(K.std()),'arithmetic_bits':int(bits),'symbol_bits':int(nb),'maxerr':me};rows.append(row);print(json.dumps(row,indent=2),flush=True)
        json.dump({'global_std':gstd,'eps':eps,'rows':rows,'scope':'Untuned four-regime promotion of PR #457. The exact same decoder-real prefix-trained bounded nonlocal residual stencil and four-expert Bayesian probability mixer are rerun without adding region-specific parameters. Nonlocal tap IDs/float32 coefficients/framing are fully charged; exact mixed-arithmetic K decoding, source replay and unchanged max error are mandatory. Baseline AR32, baseline mixer, nonlocal ordinary arithmetic, combined nonlocal+mixer and matched SZ3 are rerun on hard/easy/medium/far 128x8192. No AI. Draft/do not merge.'},open('imperial_ar32_nonlocal_bayesian_fourregions.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
