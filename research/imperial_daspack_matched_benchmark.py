import json,sys,time,importlib.metadata
import h5py,numpy as np
from daspack import DASCoder,Quantizer
import imperial_decoder_phase_automaton as m

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
C=128;NT=8192;TRAIN=1024;P=32;STEP=267;TB=1024;MODEL_BYTES=177
ORDERS=(1,2,3)


def fit_shared_ar(X):
 rows=[];ys=[]
 for c in range(C):
  x=np.asarray(X[c,:TRAIN],np.float64)
  for t in range(P,TRAIN):
   rows.append(np.r_[1.0,x[t-P:t][::-1]]);ys.append(x[t])
 return np.linalg.lstsq(np.asarray(rows,np.float64),np.asarray(ys,np.float64),rcond=None)[0].astype(np.float32)


def run_ar(X,coef):
 R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);a=float(coef[0]);b=np.asarray(coef[1:],np.float32)
 for c in range(C):
  for t in range(X.shape[1]):
   p=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
   k=int(np.rint((float(X[c,t])-p)/STEP));K[c,t]=k;R[c,t]=p+STEP*k
 return R,K


def ar_bytes(K):
 total=MODEL_BYTES;reps={}
 for t0 in range(0,K.shape[1],TB):
  A=K[:,t0:min(t0+TB,K.shape[1])];n,rep,D=m.encode_k(A)
  if not np.array_equal(A,D):raise RuntimeError(('AR K decode',t0,rep))
  total+=n;reps[rep]=reps.get(rep,0)+1
 return total,reps


def sz_bytes(X,eps):
 total=0;rows=[]
 for t0 in range(0,X.shape[1],TB):
  b,ori=m.szrun(X[:,t0:min(t0+TB,X.shape[1])],eps);total+=b;rows.append({'t0':t0,'bytes':b,'orientation':ori})
 return total,rows


def blocksets(shape,orientation):
 h,w=shape
 # Official default plus DAS-shaped blocks preserving roughly 1024/2048 time samples.
 if orientation=='TC':
  x=[('default',(1000,1000)),('time1024_fullspace',(min(1024,h),w)),('time2048_fullspace',(min(2048,h),w))]
 else:
  x=[('default',(1000,1000)),('time1024_fullspace',(h,min(1024,w))),('time2048_fullspace',(h,min(2048,w)))]
 out=[];seen=set()
 for name,b in x:
  b=(max(1,int(b[0])),max(1,int(b[1])))
  if b not in seen:out.append((name,b));seen.add(b)
 return out


def run_daspack(X,eps):
 coder=DASCoder(threads=4);q=Quantizer.Uniform(step=float(2.0*eps));rows=[]
 # X is channel x time. Test both axis conventions because DASPack's row/column LPC is not identical.
 for orientation in ('TC','CT'):
  A=np.ascontiguousarray((X.T if orientation=='TC' else X).astype(np.float64))
  for bname,bs in blocksets(A.shape,orientation):
   for order in ORDERS:
    rec={'orientation':orientation,'block_name':bname,'blocksize':list(bs),'levels':1,'order':order}
    try:
     t=time.perf_counter();stream=coder.encode(A,q,blocksize=bs,levels=1,order=order);encs=time.perf_counter()-t
     t=time.perf_counter();D=np.asarray(coder.decode(stream),np.float64);decs=time.perf_counter()-t
     if D.shape!=A.shape:raise RuntimeError(('shape',D.shape,A.shape))
     me=float(np.max(np.abs(A-D)))
     if me>eps*(1+1e-10):raise RuntimeError(('DASPack hard error',me,eps))
     n=len(stream);rec.update({'ok':True,'bytes':n,'bps':8*n/A.size,'ratio':A.nbytes/n,'maxerr':me,'encode_seconds':encs,'decode_seconds':decs})
    except Exception as e:
     rec.update({'ok':False,'error':repr(e)})
    rows.append(rec);print(json.dumps({'daspack':rec},flush=True))
 good=[r for r in rows if r.get('ok')]
 if not good:raise RuntimeError(('all DASPack candidates failed',rows))
 good.sort(key=lambda r:r['bytes'])
 return good[0],rows


def main(path):
 version=importlib.metadata.version('daspack-dev')
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
  for region,c0 in SPECS:
   X=np.asarray(d[:NT,c0:c0+C],np.float64).T
   coef=fit_shared_ar(X);R,K=run_ar(X,coef);me=float(np.max(np.abs(X-R.astype(np.float64))))
   if me>eps*(1+1e-12):raise RuntimeError((region,'AR hard',me,eps))
   ab,reps=ar_bytes(K);sb,sdetail=sz_bytes(X,eps);best,all_dp=run_daspack(X,eps)
   row={'region':region,'c0':c0,'shape_CT':list(X.shape),'samples':int(X.size),'epsilon':eps,
        'incumbent_ar32':{'bytes':ab,'bps':8*ab/X.size,'ratio':(2*X.size)/ab,'gain_vs_sz3':sb/ab,'maxerr':me,'reps':reps},
        'matched_sz3':{'bytes':sb,'bps':8*sb/X.size,'ratio':(2*X.size)/sb,'frames':sdetail},
        'daspack_best':best,'daspack_candidates':all_dp,
        'ar32_gain_vs_daspack':best['bytes']/ab,'daspack_gain_vs_sz3':sb/best['bytes']}
   rows.append(row);print(json.dumps({'region_result':row},indent=2),flush=True)
 out={'daspack_distribution':'daspack-dev','daspack_version':version,'daspack_uniform_step':2*eps,'global_std':gstd,'eps':eps,'rows':rows,
      'scope':'Matched modern DAS-specific baseline gate on the canonical Imperial Valley record. DASPack 0.0.1a0 is given Uniform(step=2*epsilon), i.e. its documented max-error budget step/2 equals the complete public epsilon, which is slightly more distortion than the incumbent integer step267. Its complete self-describing stream length is counted with no hidden model bytes. Every stream is decoded and max error independently verified. Both channel/time orientations are tested because the codec uses row/column LPC, with official default and fixed DAS-shaped 1024/2048-time block geometries and orders 1/2/3, levels=1. Current persistent shared AR32 step267 and matched tiled SZ3 are rerun on identical 128x8192 samples. No AI. Diagnostic benchmark; do not merge.'}
 json.dump(out,open('imperial_daspack_matched_benchmark.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
