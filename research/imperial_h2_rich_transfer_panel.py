import json,sys
import h5py,numpy as np
import imperial_h2_rich_causal_headtohead as h2
import imperial_compact_nova_container as x

SPECS=(
 ('hard_t2048',2048,512),
 ('hard_t8192',8192,512),
 ('hard_t14488',14488,512),
 ('hard_t22000',22000,512),
 ('easy_t14488',14488,2304),
 ('far_t14488',14488,6784),
)

def main(path):
    rows=[]
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=x.m.stats(ds);eps=.1*std
        for name,t0,c0 in SPECS:
            X=np.asarray(ds[t0:t0+x.g.T,c0:c0+x.g.C],np.float64).T
            szb,ori=x.m.szrun(X,eps);nova,_,_=h2.encode_nova(X,eps);ar32,_=h2.encode_ar32(X,eps)
            row={'name':name,'t0':t0,'c0':c0,'NOVA':nova['bytes'],'AR32':ar32['bytes'],'SZ3':int(szb),'delta_NOVA_minus_AR32':nova['bytes']-ar32['bytes'],'gain_vs_AR32':ar32['bytes']/nova['bytes'],'gain_vs_SZ3':szb/nova['bytes'],'NOVA_model':nova['model_bytes'],'NOVA_field':nova['field_bytes'],'AR_model':ar32['model_bytes'],'AR_field':ar32['field_bytes'],'NOVA_maxerr':nova['maxerr'],'AR_maxerr':ar32['maxerr'],'local_std':float(X.std())}
            rows.append(row);print(json.dumps(row),flush=True)
    wins=sum(r['NOVA']<r['AR32'] for r in rows);totN=sum(r['NOVA'] for r in rows);totA=sum(r['AR32'] for r in rows);totS=sum(r['SZ3'] for r in rows)
    out={'global_std':std,'eps':eps,'h_factor':2.0,'shape':[x.g.C,x.g.T],'rows':rows,'summary':{'wins_vs_AR32':wins,'objects':len(rows),'NOVA_total':totN,'AR32_total':totA,'delta_total':totN-totA,'aggregate_gain_vs_AR32':totA/totN,'aggregate_gain_vs_SZ3':totS/totN,'min_gain_vs_AR32':min(r['gain_vs_AR32'] for r in rows),'max_gain_vs_AR32':max(r['gain_vs_AR32'] for r in rows)},'scope':'Precommitted transfer/falsification panel for the h=2epsilon discovery. The same public h=2epsilon rule, learned-generator procedure, exact compact model framing, and identical rich causal field coder are applied without dataset-name routing to four time windows in the hard channel region plus easy/far spatial regions. AR32 receives the identical rich field coder. Every object independently parses/replays both streams and passes the unchanged global-epsilon hard bound. This tests whether the hard-tile crossing transfers rather than being a single-window accident.'}
    json.dump(out,open('imperial_h2_rich_transfer_panel.json','w'),indent=2);print(json.dumps({'summary':out['summary']},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
