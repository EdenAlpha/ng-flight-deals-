import json,math,sys
import h5py,numpy as np
sys.path.append('research')
import imperial_dyadic_legal_grid_full_array as m

SPECS=(('hard',14488,512),('easy',14488,2304),('medium',14488,4608),('far',14488,6784))
CB=128;TB=1024;STEP=256


def encode_phase(X,eps,phase):
    q=np.rint((X-float(phase))/STEP).astype(np.int32)
    R0=float(phase)+q.astype(np.float64)*STEP
    me0=float(np.max(np.abs(X-R0)))
    if me0>eps*(1+1e-12):raise RuntimeError(('phase hard',phase,me0,eps))
    c=m.signed_reps(q)+m.xor_reps(q)+[m.bitplane_rep(q,False),m.bitplane_rep(q,True),m.byteshuffle_rep(q)]
    best=min(c,key=lambda x:x[0])
    R=float(phase)+best[2].astype(np.float64)*STEP
    me=float(np.max(np.abs(X-R)))
    if me>eps*(1+1e-12):raise RuntimeError(('decode hard',phase,me,eps,best[1]))
    # 1 byte phase + 8 bytes fixed local framing beyond parent's representation bytes.
    return {'bytes':best[0]+9,'phase':int(phase),'rep':best[1],'maxerr':me,'zero_fraction':float(np.mean(q==0))}


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;rows=[]
        for name,t0,c0 in SPECS:
            X=np.asarray(d[t0:t0+TB,c0:c0+CB],np.float64).T
            sb,ori=m.szrun(X,eps)
            candidates=[]
            for phase in range(256):
                r=encode_phase(X,eps,phase);candidates.append(r)
            candidates.sort(key=lambda r:r['bytes'])
            fixed=next(r for r in candidates if r['phase']==0)
            best=candidates[0]
            row={'tile':name,'t0':t0,'c0':c0,'sz3_bytes':sb,'sz3_orientation':ori,
                 'fixed_phase0':fixed,'best':best,'gain_best_vs_sz3':sb/best['bytes'],
                 'gain_best_vs_fixed0':fixed['bytes']/best['bytes'],
                 'best_bps':8*best['bytes']/X.size,'sz3_bps':8*sb/X.size,
                 'top16':candidates[:16]}
            rows.append(row);print(json.dumps(row),flush=True)
        ob=sum(r['best']['bytes'] for r in rows);fb=sum(r['fixed_phase0']['bytes'] for r in rows);sb=sum(r['sz3_bytes'] for r in rows);n=CB*TB*len(rows)
        out={'global_std':std,'eps':eps,'step':STEP,'phases_tested':256,'rows':rows,
             'aggregate':{'best_bytes':ob,'fixed_phase0_bytes':fb,'sz3_bytes':sb,'best_bps':8*ob/n,
                          'fixed_phase0_bps':8*fb/n,'sz3_bps':8*sb/n,'gain_best_vs_sz3':sb/ob,
                          'gain_best_vs_fixed0':fb/ob,'min_tile_gain':min(r['gain_best_vs_sz3'] for r in rows)},
             'scope':'Exhaustive legal byte-grid phase synthesis. For each of four precommitted 128x1024 Imperial hard/easy/medium/far tiles, every integer phase 0..255 of the 256-spaced reconstruction lattice is tested. Every phase has worst-case source error <=128, strictly below the unchanged public 10%-global-std epsilon. Each phase uses the exact decoder-real representation menu from PR287/288; one transmitted phase byte is counted, the winning frame is byte-decoded, and final hard error is verified. Matched SZ3 is rerun identically. Patch screen only; no whole-array claim and no target-trained probability model.'}
        print(json.dumps({'aggregate':out['aggregate']},indent=2),flush=True);json.dump(out,open('imperial_dyadic_phase_synthesis.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
