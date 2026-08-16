import json,sys
import h5py,numpy as np
import imperial_h2_rich_causal_headtohead as h2
import imperial_compact_nova_container as x

def main(path,name,t0,c0):
    t0=int(t0);c0=int(c0)
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=x.m.stats(ds);eps=.1*std;X=np.asarray(ds[t0:t0+x.g.T,c0:c0+x.g.C],np.float64).T
    szb,ori=x.m.szrun(X,eps);nova,_,_=h2.encode_nova(X,eps);ar32,_=h2.encode_ar32(X,eps)
    row={'name':name,'t0':t0,'c0':c0,'NOVA':nova['bytes'],'AR32':ar32['bytes'],'SZ3':int(szb),'delta_NOVA_minus_AR32':nova['bytes']-ar32['bytes'],'gain_vs_AR32':ar32['bytes']/nova['bytes'],'gain_vs_SZ3':szb/nova['bytes'],'NOVA_model':nova['model_bytes'],'NOVA_field':nova['field_bytes'],'AR_model':ar32['model_bytes'],'AR_field':ar32['field_bytes'],'NOVA_maxerr':nova['maxerr'],'AR_maxerr':ar32['maxerr'],'local_std':float(X.std()),'global_std':std,'eps':eps}
    fn=f'imperial_h2_transfer_{name}.json';json.dump(row,open(fn,'w'),indent=2);print(json.dumps({'summary':row},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4])
