import json,sys
import h5py,numpy as np
import imperial_strong_ar_family_audit as a
import imperial_compact_nova_container as x


def main(path,p,scope):
    p=int(p)
    if (p,scope) not in a.CANDS:raise RuntimeError(('candidate',p,scope))
    cid=a.CANDS.index((p,scope))
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=x.m.stats(ds);eps=.1*std;X=np.asarray(ds[x.g.T0:x.g.T0+x.g.T,x.g.C0:x.g.C0+x.g.C],np.float64).T
    szb,ori=x.m.szrun(X,eps);r=a.materialize(X,eps,cid,p,scope);r['gain_vs_sz3']=szb/r['bytes']
    out={'global_std':std,'eps':eps,'sz3_bytes':int(szb),'candidate':r}
    fn=f'imperial_strong_ar_{scope}_p{p}.json';json.dump(out,open(fn,'w'),indent=2)
    print(json.dumps({'summary':{k:v for k,v in r.items() if k!='field_detail'}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1],sys.argv[2],sys.argv[3])
