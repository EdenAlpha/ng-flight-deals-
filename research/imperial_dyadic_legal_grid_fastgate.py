import json,sys
import h5py,numpy as np
import imperial_dyadic_legal_grid_full_array as m

SPECS=(('hard',14488,512),('easy',14488,2304),('medium',14488,4608),('far',14488,6784))

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;rows=[]
        for name,t0,c0 in SPECS:
            X=np.asarray(d[t0:t0+m.TB,c0:c0+m.CB],np.float64).T
            ours=m.encode_dyadic(X,eps);sb,ori=m.szrun(X,eps)
            row={'tile':name,'t0':t0,'c0':c0,'ours_bytes':ours['bytes'],'ours_rep':ours['rep'],'sz3_bytes':sb,'gain_vs_sz3':sb/ours['bytes'],'ours_bps':8*ours['bytes']/X.size,'sz3_bps':8*sb/X.size,'maxerr':ours['maxerr'],'zero_fraction':ours['zero_fraction'],'sz3_orientation':ori,'local_std':float(X.std()),'eps_over_local_std':eps/float(X.std())}
            rows.append(row);print(json.dumps(row),flush=True)
        ob=sum(r['ours_bytes'] for r in rows);sb=sum(r['sz3_bytes'] for r in rows);n=m.CB*m.TB*len(rows)
        out={'global_std':std,'eps':eps,'dyadic_step':m.STEP,'worst_quantization_error':m.STEP/2,'rows':rows,'aggregate':{'ours_bytes':ob,'sz3_bytes':sb,'gain_vs_sz3':sb/ob,'ours_bps':8*ob/n,'sz3_bps':8*sb/n,'min_tile_gain':min(r['gain_vs_sz3'] for r in rows)},'scope':'Fast directional gate for PR #287. Identical frozen 256-grid codec and representation menu on four precommitted hard/easy/medium/far 128x1024 Imperial tiles; matched SZ3 and unchanged global 10%-std hard error. No tuning and no whole-array claim.'}
        print(json.dumps(out['aggregate'],indent=2));json.dump(out,open('imperial_dyadic_legal_grid_fastgate.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
