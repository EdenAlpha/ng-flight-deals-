import json
import numpy as np
from pysz import sz,szConfig,szErrorBoundMode
meta=json.load(open('data/forge_subcube_meta.json'))
X=np.fromfile('data/forge_subcube_f32.bin','<f4').reshape(meta['shape'])
eps=float(meta['eps_10pct_std']); raw=X.nbytes

def comp(A,e):
    A=np.ascontiguousarray(A,dtype=np.float32);c=szConfig();c.errorBoundMode=szErrorBoundMode.ABS;c.absErrorBound=float(e);b,_=sz.compress(A,c);D,_=sz.decompress(b,np.float32,A.shape);return int(b.size),D

def project_axis(Y,delta,axis,kind,max_stride):
    lo=X-delta;hi=X+delta;n=Y.shape[axis]
    strides=[];s=2
    while s<=max_stride and s<n:strides.append(s);s*=2
    for s in strides[::-1]:
        for a in range(0,n-1,s):
            b=min(n-1,a+s);m=a+(b-a)//2
            if m==a or m==b:continue
            ya=np.take(Y,a,axis=axis);yb=np.take(Y,b,axis=axis)
            if kind==0:
                pred=.5*(ya+yb)
            else:
                oa=a-(b-a);ob=b+(b-a)
                if oa>=0 and ob<n:
                    yoa=np.take(Y,oa,axis=axis);yob=np.take(Y,ob,axis=axis);pred=(-yoa+9*ya+9*yb-yob)/16.0
                else:pred=.5*(ya+yb)
            sl=[slice(None)]*3;sl[axis]=m;sl=tuple(sl);Y[sl]=np.clip(pred,lo[sl],hi[sl])
    return Y

def shape(df,order,kind,max_stride,rounds):
    delta=df*eps;Y=X.copy()
    for _ in range(rounds):
        for axis in order:Y=project_axis(Y,delta,axis,kind,max_stride)
    return Y

b,D=comp(X,eps);base={'bytes':b,'ratio':raw/b,'maxerr':float(np.max(np.abs(X-D)))};print('BASE',json.dumps(base),flush=True)
rows=[]
orders=[(2,),(2,0,1),(0,1,2),(2,1,0),(0,2,1)]
for df in [.1,.2,.3,.4,.5,.6,.7,.8,.9]:
  for order in orders:
   for kind in [0,1]:
    for ms in [8,16,32,64]:
     for rounds in [1,2]:
        Y=shape(df,order,kind,ms,rounds);bb,Z=comp(Y,eps-df*eps)
        r={'delta_frac':df,'order':order,'kind':kind,'max_stride':ms,'rounds':rounds,'bytes':bb+24,'ratio':raw/(bb+24),'morph_max':float(np.max(np.abs(X-Y))),'final_maxerr':float(np.max(np.abs(X-Z)))};rows.append(r);print('INTERP',json.dumps(r),flush=True)
rows.sort(key=lambda r:r['bytes']);best=rows[:25];print('BEST',json.dumps(best,indent=2),flush=True)
open('forge_surrogate_interp_results.json','w').write(json.dumps({'base':base,'eps':eps,'raw':raw,'best':best},indent=2))
