import json,sys
import h5py,numpy as np
import imperial_exact2_fair_rich_ar32 as e

SPECS=((512,0),(512,4096),(512,8192),(512,12288),(512,14488),(512,16384),(512,20480),(512,24576),(512,28976),(544,14488),(576,14488),(608,14488))
C=32;T=1024


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=e.x.m.stats(ds);eps=.1*std
        rows=[]
        for c0,t0 in SPECS:
            X=np.asarray(ds[t0:t0+T,c0:c0+C],np.float64).T
            szb,ori=e.x.m.szrun(X,eps)
            h,lo,hi,Q,D,dts,dcs,co,intercept,pchg,cchg,score=e.build_exact2(X,eps)
            nova=e.materialize_nova(X,eps,h,Q,D,dts,dcs,co,intercept,False)
            ar=e.rich_ar32(X,eps)
            row={'c0':int(c0),'t0':int(t0),'samples':int(X.size),'nova_bytes':int(nova['bytes']),'rich_ar32_bytes':int(ar['bytes']),'sz3_bytes':int(szb),'gain_vs_rich_ar32':ar['bytes']/nova['bytes'],'gain_vs_sz3':szb/nova['bytes'],'delta_vs_rich_ar32':nova['bytes']-ar['bytes'],'nova_maxerr':nova['maxerr'],'ar32_maxerr':ar['maxerr'],'mean_legal_states':float(np.mean(hi.astype(np.int64)-lo.astype(np.int64)+1)),'projection_changes':int(pchg),'causal_changes':int(cchg),'causal_surrogate_bits':float(score),'sz3_orientation':ori}
            rows.append(row);print(json.dumps(row),flush=True)
    ours=sum(r['nova_bytes'] for r in rows);ar=sum(r['rich_ar32_bytes'] for r in rows);sz=sum(r['sz3_bytes'] for r in rows);n=sum(r['samples'] for r in rows)
    agg={'tiles':len(rows),'samples':n,'nova_bytes':ours,'rich_ar32_bytes':ar,'sz3_bytes':sz,'gain_vs_rich_ar32':ar/ours,'gain_vs_sz3':sz/ours,'delta_vs_rich_ar32':ours-ar,'wins_rich_ar32':sum(r['nova_bytes']<r['rich_ar32_bytes'] for r in rows),'ties_rich_ar32':sum(r['nova_bytes']==r['rich_ar32_bytes'] for r in rows),'wins_sz3':sum(r['nova_bytes']<r['sz3_bytes'] for r in rows),'min_gain_vs_rich_ar32':min(r['gain_vs_rich_ar32'] for r in rows),'max_gain_vs_rich_ar32':max(r['gain_vs_rich_ar32'] for r in rows),'bps_nova':8*ours/n,'bps_rich_ar32':8*ar/n,'bps_sz3':8*sz/n}
    out={'global_std':std,'eps':eps,'h_factor':e.HFAC,'shape':[C,T],'specs':[list(v) for v in SPECS],'rows':rows,'aggregate':agg,'scope':'Twelve-tile decoder-real generalization of the exact h=2.0*epsilon NOVA coordinate system from PR573/PR585 against the strongest known rich-causal AR32 representation. The public codec is fixed across all tiles: each tile independently fits and fully charges the same sparse causal NOVA generator, uses the exact-2epsilon reconstruction lattice, materializes the compact causal defect stream, parses it to EOF, replays Q and checks the unchanged source hard error. AR32 is independently rebuilt per identical tile and its K field is encoded with the richer causal grammar from PR570, parsed/replayed and hard-error checked. Matched SZ3 is rerun on each tile. No per-tile method routing or oracle selection is used; aggregate bytes are literal sums of complete streams.'}
    json.dump(out,open('imperial_exact2_rich_hard_panel.json','w'),indent=2)
    print(json.dumps({'summary':agg},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
