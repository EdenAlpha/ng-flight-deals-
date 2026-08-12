import json,os,sys
import numpy as np
from pysz import sz,szConfig,szErrorBoundMode
from research.imperial_valley_frozen_brady_transfer import encode_tile,decode_tile,SAFETY

TIME=1024

def parse(path):
    size=os.path.getsize(path);h=open(path,'rb').read(3600);cand=[]
    for bo,nb in [('big','>'),('little','<')]:
        dt=int.from_bytes(h[3216:3218],bo);ns=int.from_bytes(h[3220:3222],bo);fmt=int.from_bytes(h[3224:3226],bo);st=240+4*ns
        if fmt==5 and dt>0 and ns>0 and (size-3600)%st==0:cand.append((nb,ns,(size-3600)//st,st))
    if not cand:raise RuntimeError('parse')
    nb,ns,ntr,st=cand[0];mm=np.memmap(path,np.uint8,'r');A=np.ndarray((ntr,ns),dtype=np.dtype(nb+'f4'),buffer=mm,offset=3840,strides=(st,4))
    s=ss=0.0;n=0
    for i in range(0,ntr,256):
        x=A[i:min(i+256,ntr)].astype(np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
    mu=s/n;global_std=float(np.sqrt(max(0,ss/n-mu*mu)))
    X=A[4096:4224,6000:14192].astype(np.float32,copy=True)
    block_std=float(X.std(dtype=np.float64))
    return X,global_std,block_std

def run_exact(X,public_eps):
    internal=public_eps*SAFETY;total=64;maxerr=0.0;nz_num=0.0;nz_den=0;tiles=[]
    for t0 in range(0,X.shape[1],TIME):
        W=X[:,t0:t0+TIME]
        blob,me,diag=encode_tile(W,internal)
        R=decode_tile(blob,internal)
        me2=float(np.max(np.abs(W-R)))
        if me2>public_eps*(1+3e-6):raise RuntimeError(('hard error',t0,me2,public_eps))
        total+=len(blob);maxerr=max(maxerr,me2);nz_num+=diag['correction_nonzero_fraction']*W.size;nz_den+=W.size
        tiles.append({'t0':t0,'bytes':len(blob),'ratio':W.nbytes/len(blob),'correction_nonzero_fraction':diag['correction_nonzero_fraction'],'maxerr':me2})
    return {'bytes':total,'ratio':X.nbytes/total,'maxerr':maxerr,'correction_nonzero_fraction':nz_num/nz_den,'tiles':tiles}

def run_sz3(X,eps):
    cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
    best=None
    for name,A in [('channel_time',np.ascontiguousarray(X)),('time_channel',np.ascontiguousarray(X.T))]:
        b,_=sz.compress(A,cfg);R,_=sz.decompress(b,np.float32,A.shape);me=float(np.max(np.abs(A-R)))
        row={'orientation':name,'bytes':int(b.size),'ratio':X.nbytes/int(b.size),'maxerr':me}
        if best is None or row['bytes']<best['bytes']:best=row
    return best

def main(path):
    X,gstd,bstd=parse(path);raw=X.nbytes
    cases={}
    for mode,eps in [('file_global_10pct',0.1*gstd),('active_block_10pct',0.1*bstd)]:
        exact=run_exact(X,eps);base=run_sz3(X,eps)
        cases[mode]={'public_eps':eps,'exact_brady_transfer':exact,'matched_sz3':base,'gain_vs_sz3':base['bytes']/exact['bytes']}
        print(mode,json.dumps(cases[mode],indent=2),flush=True)
    out={'shape':list(X.shape),'raw_bytes':raw,'file_global_std':gstd,'active_block_std':bstd,'global_std_over_block_std':gstd/bstd,'cases':cases}
    json.dump(out,open('brady_active_block_local_epsilon_audit.json','w'),indent=2)
    print(json.dumps(out,indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
