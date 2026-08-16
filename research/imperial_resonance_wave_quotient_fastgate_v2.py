import json,sys
from fractions import Fraction
import h5py,numpy as np,zstandard as zstd
from scipy.optimize import linprog
from scipy.sparse import coo_matrix,hstack,vstack,eye
sys.path.insert(0,__file__.rsplit('/',1)[0])
import imperial_huber_ar32_coldstart_arithmetic_regions as base
NX=32;NT=256;FRAME=112
REGIONS=(('hard',512),('easy',2304));LAM_NUMS=(0,1,2,3,4,5,6,7,8,9,10,12,14,16,20,24,28,32);LAM_DEN=16
Z=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()
def frac_for(n):return Fraction(n,LAM_DEN)
def build_A(lam):
 rows=[];cols=[];vals=[];r=0
 for t in range(1,NT-1):
  for x in range(1,NX-1):
   rows += [r]*5;cols += [(t+1)*NX+x,t*NX+x,(t-1)*NX+x,t*NX+x+1,t*NX+x-1];vals += [1.,-2.+2.*lam,1.,-lam,-lam];r+=1
 A=coo_matrix((vals,(rows,cols)),shape=(r,NT*NX)).tocsr();B=coo_matrix((np.ones(r),(np.arange(r),np.repeat(np.arange(NT-2),NX-2))),shape=(r,NT-2)).tocsr();return A,B
def solve(X,eps,fr,weights=None):
 A,B=build_A(float(fr));m=A.shape[0];n=NT*NX;nh=NT-2
 if weights is None:weights=np.ones(m)
 U=eye(m,format='csr');Aub=vstack([hstack([A,-B,-U]),hstack([-A,B,-U])]).tocsr();c=np.r_[np.zeros(n+nh),weights]
 lo=np.ceil(X.ravel()-eps).astype(np.int64);hi=np.floor(X.ravel()+eps).astype(np.int64);bounds=[(float(lo[i]),float(hi[i])) for i in range(n)]+[(None,None)]*nh+[(0,None)]*m
 rr=linprog(c,A_ub=Aub,b_ub=np.zeros(2*m),bounds=bounds,method='highs',options={'presolve':True})
 if not rr.success:raise RuntimeError((str(fr),rr.status,rr.message))
 y=np.rint(rr.x[:n]).astype(np.int64);y=np.minimum(hi,np.maximum(lo,y)).reshape(NT,NX).astype(np.int32);p,q=fr.numerator,fr.denominator
 h=np.zeros(NT-2,np.int32);R=np.zeros((NT-2,NX-2),np.int32)
 for ti,t in enumerate(range(1,NT-1)):
  d=np.asarray([q*int(y[t+1,x])+(-2*q+2*p)*int(y[t,x])+q*int(y[t-1,x])-p*int(y[t,x+1])-p*int(y[t,x-1]) for x in range(1,NX-1)],np.int64)
  h[ti]=int(np.rint(np.median(d.astype(np.float64))/q));R[ti]=d-q*int(h[ti])
 return y,h,R,float(rr.fun)
def pack(a):
 a=np.asarray(a);mn=int(a.min()) if a.size else 0;mx=int(a.max()) if a.size else 0;dt=np.int16 if -32768<=mn and mx<=32767 else np.int32;code='<i2' if dt is np.int16 else '<i4';q=np.asarray(a,dtype=dt).ravel()
 dense=Z.compress(q.astype(code).tobytes());nz=np.flatnonzero(q!=0).astype('<u4');v=q[nz].astype(code);ib=Z.compress(nz.tobytes());vb=Z.compress(v.tobytes());mb=Z.compress(np.packbits((q!=0).astype(np.uint8),bitorder='little').tobytes());c=[('dense',len(dense),[dense]),('sparse_idx',len(ib)+len(vb),[ib,vb]),('bitmap',len(mb)+len(vb),[mb,vb])];mode,n,parts=min(c,key=lambda x:x[1])
 if mode=='dense':d=np.frombuffer(ZD.decompress(parts[0]),dtype=code)
 elif mode=='sparse_idx':
  ii=np.frombuffer(ZD.decompress(parts[0]),'<u4');vv=np.frombuffer(ZD.decompress(parts[1]),dtype=code);d=np.zeros_like(q);d[ii]=vv
 else:
  mk=np.unpackbits(np.frombuffer(ZD.decompress(parts[0]),np.uint8),bitorder='little')[:q.size].astype(bool);vv=np.frombuffer(ZD.decompress(parts[1]),dtype=code);d=np.zeros_like(q);d[mk]=vv
 if not np.array_equal(d,q):raise RuntimeError(('pack',mode));
 return {'mode':mode,'bytes':n},d.reshape(a.shape)
def codec(X,eps,fr,irls=False):
 y,h,r,obj=solve(X,eps,fr)
 if irls:
  w=np.minimum(1./(np.abs(r.astype(np.float64)).ravel()+1.),1000.);y,h,r,obj=solve(X,eps,fr,w)
 mask=np.zeros((NT,NX),bool);mask[:2]=True;mask[2:,0]=True;mask[2:,-1]=True;pb,bd=pack(y[mask]);ph,hd=pack(h);pr,rd=pack(r);total=FRAME+pb['bytes']+ph['bytes']+pr['bytes'];p,q=fr.numerator,fr.denominator;yd=np.zeros_like(y);bi=0
 for t in range(NT):
  for x in range(NX):
   if t<2 or x in (0,NX-1):yd[t,x]=int(bd.ravel()[bi]);bi+=1
 for ti,t in enumerate(range(1,NT-1)):
  for xi,x in enumerate(range(1,NX-1)):
   num=int(rd[ti,xi])+q*int(hd[ti])-(-2*q+2*p)*int(yd[t,x])-q*int(yd[t-1,x])+p*int(yd[t,x+1])+p*int(yd[t,x-1])
   if num%q:raise RuntimeError(('div',str(fr),t,x,num,q));yd[t+1,x]=num//q
   yd[t+1,x]=num//q
 if bi!=bd.size or not np.array_equal(yd,y):raise RuntimeError(('decode',str(fr),int(np.count_nonzero(yd!=y))))
 me=float(np.max(np.abs(X-yd.astype(np.float64))));
 if me>eps*(1+1e-12):raise RuntimeError(('hard',str(fr),me,eps))
 return {'lambda':float(fr),'fraction':f'{p}/{q}','irls':irls,'bytes':int(total),'bps':8*total/X.size,'maxerr':me,'defect_zero_fraction':float(np.mean(r==0)),'defect_mean_abs_scaled':float(np.mean(np.abs(r.astype(np.float64)))),'boundary_bytes':pb['bytes'],'shared_state_bytes':ph['bytes'],'defect_bytes':pr['bytes'],'defect_mode':pr['mode'],'lp_objective':obj}
def baseline(X,eps):
 old=(base.C,base.NT,base.TRAIN);base.C=NX;base.NT=NT;base.TRAIN=64
 try:
  _,co=base.fits(X.T);R,K=base.run_ar(X.T,co);ab,_,_,Kd=base.arithmetic(K);Rd=base.decode_source(Kd,co)
  if not np.array_equal(Rd,R):raise RuntimeError('AR replay')
  ame=float(np.max(np.abs(X.T-Rd.astype(np.float64))))
 finally:base.C,base.NT,base.TRAIN=old
 sz,_=base.m.szrun(np.ascontiguousarray(X.T.astype(np.float32)),eps);return {'ar32_bytes':int(ab),'ar32_bps':8*ab/X.size,'ar32_maxerr':ame,'sz3_bytes':int(sz),'sz3_bps':8*int(sz)/X.size}
def main(path):
 with h5py.File(path,'r') as f:
  ds=f['Acoustic'];_,std=base.m.stats(ds);eps=.1*std;rows=[];print(json.dumps({'std':std,'eps':eps,'tile':[NT,NX]}),flush=True)
  for region,c0 in REGIONS:
   X=np.asarray(ds[:NT,c0:c0+NX],np.int32);b=baseline(X,eps);cand=[]
   for n in LAM_NUMS:
    z=codec(X,eps,frac_for(n));z.update({'region':region,'c0':c0,**b,'gain_vs_ar32':b['ar32_bytes']/z['bytes'],'gain_vs_sz3':b['sz3_bytes']/z['bytes']});cand.append(z);print(json.dumps(z),flush=True)
   for z0 in sorted(cand,key=lambda z:z['bytes'])[:3]:
    z=codec(X,eps,Fraction(z0['fraction']),True);z.update({'region':region,'c0':c0,**b,'gain_vs_ar32':b['ar32_bytes']/z['bytes'],'gain_vs_sz3':b['sz3_bytes']/z['bytes']});cand.append(z);print(json.dumps(z),flush=True)
   rows+=cand;print(json.dumps({'region_summary':region,'baseline':b,'best':min(cand,key=lambda z:z['bytes']),'sparsest':max(cand,key=lambda z:z['defect_zero_fraction'])},indent=2),flush=True)
 json.dump({'std':std,'eps':eps,'rows':rows,'scope':'Fixed v2 reconstructable compression-resonance second-order wave gate; global hard-box projection, rational wave operator, shared time forcing, exact boundary/shared-state/defect streams, byte round-trip and causal source replay.'},open('imperial_resonance_wave_quotient_fastgate_v2.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
