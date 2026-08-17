import json,sys
import h5py
import numpy as np
import imperial_valley_frozen_brady_transfer as m

SPACE=m.SPACE
TIME=m.TIME

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic']
        _,std=m.stats(d)
        public_eps=.1*std
        internal_eps=public_eps*m.SAFETY
        rows=[]
        total=64
        maxerr=0.0
        for s0 in range(0,d.shape[1],SPACE):
            s1=min(d.shape[1],s0+SPACE)
            b=0
            tiles=0
            nz_num=0.0
            ns=0
            modes={str(i):0 for i in range(4)}
            for t0 in range(0,d.shape[0],TIME):
                t1=min(d.shape[0],t0+TIME)
                W=np.asarray(d[t0:t1,s0:s1]).T.astype(np.float32,copy=False)
                blob,me,diag=m.encode_tile(W,internal_eps)
                if me>public_eps*(1+3e-6):
                    raise RuntimeError(('hard',s0,t0,me,public_eps))
                b+=len(blob);tiles+=1;maxerr=max(maxerr,me)
                nz_num+=diag['correction_nonzero_fraction']*W.size;ns+=W.size
                modes[str(diag['mode'])]+=1
            row={'cb':s0//SPACE,'c0':s0,'channels':s1-s0,'samples':ns,'spectral_bytes':b,'spectral_bps':8*b/ns,'correction_nonzero_fraction':nz_num/ns,'tiles':tiles,'mode_counts':modes}
            rows.append(row);total+=b
            print(json.dumps(row),flush=True)
        out={'global_std':std,'eps':public_eps,'rows':rows,'container_bytes':total,'maxerr':maxerr,'scope':'Exact PR206 frozen Brady spectral codec, regrouped only by contiguous 128-channel cable block. Byte streams and hard-error semantics unchanged.'}
        json.dump(out,open('imperial_spectral_block_accounting.json','w'),indent=2)
        print(json.dumps({'summary':{'container_bytes':total,'maxerr':maxerr}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
