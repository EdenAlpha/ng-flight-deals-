import json,math,sys
from fractions import Fraction
import h5py,numpy as np,zstandard as zstd
from scipy.optimize import linprog
from scipy.sparse import coo_matrix,hstack,vstack,eye
sys.path.insert(0,__file__.rsplit('/',1)[0])
import imperial_huber_ar32_coldstart_arithmetic_regions as base

NX=32;NT=256;FRAME=112
REGIONS=(('hard',512),('easy',2304))
# Fixed public sweep; Fraction reduces each rational to its minimal exact decoder denominator.
LAM_NUMS=(0,1,2,3,4,5,6,7,8,9,10,12,14,16,20,24,28,32)
LAM_DEN=16
Z=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()

def frac_for(n):return Fraction(n,LAM_DEN)

def build_A(nt,nx,lam):
 rows=[];cols=[];vals=[];ts=[];r=0
 for t in range(1,nt-1):
  for x in range(1,nx-1):
   rows += [r]*5
   cols += [(t+1)*nx+x,t*nx+x,(t-1)*nx+x,t*nx+x+1,t*nx+x-1]
   vals += [1.0,-2.0+2.0*lam,1.0,-lam,-lam]
   ts.append(t);r+=1
 A=coo_matrix((np.asarray(vals),(np.asarray(rows),np.asarray(cols))),shape=(r,nt*nx)).tocsr()
 br=np.arange(r,dtype=np.int64);bc=np.repeat(np.arange(nt-2,dtype=np.int64),nx-2);B=coo_matrix((np.ones(r),(br,bc)),shape=(r,nt-2)).tocsr()
 return A,B

def solve(X,eps,fr,weights=None):
 lam=float(fr);A,B=build_A(NT,NX,lam);m=A.shape[0];n=NT*NX;nh=NT-2
 if weights is None:weights=np.ones(m,np.float64)
 c=np.r_[np.zeros(n+nh),weights];U=eye(m,format='csr')
 Aub=vstack([hstack([A,-B,-U],format='csr'),hstack([-A,B,-U],format='csr')],format='csr')
 lo=np.ceil(X.ravel()-eps).astype(np.int64);hi=np.floor(X.ravel()+eps).astype(np.int64)
 bounds=[(float(lo[i]),float(hi[i])) for i in range(n)]+[(None,None)]*nh+[(0,None)]*m
 rr=linprog(c,A_ub=Aub,b_ub=np.zeros(2*m),bounds=bounds,method='highs',options={'presolve':True})
 if not rr.success:raise RuntimeError((str(fr),rr.status,rr.message))
 y=np.rint(rr.x[:n]).astype(np.int64);y=np.minimum(hi,np.maximum(lo,y)).reshape(NT,NX).astype(np.int32)
 p,q=fr.numerator,fr.denominator
 # Exact integer scaled defect. Choose integer shared h[t] by median in the scaled domain.
 h=np.zeros(NT-2,np.int32);R=np.zeros((NT-2,NX-2),np.int32)
 for ti,t in enumerate(range(1,NT-1)):
  d=[]
  for x in range(1,NX-1):
   z=q*int(y[t+1,x])+(-2*q+2*p)*int(y[t,x])+q*int(y[t-1,x])-p*int(y[t,x+1])-p*int(y[t,x-1]);d.append(z)
  hh=int(np.rint(np.median(np.asarray(d,np.float64))/q));h[ti]=hh
  for xi,z in enumerate(d):R[ti,xi]=int(z-q*hh)
 return y,h,R,float(rr.fun)

def exact_pack(a):
 a=np.asarray(a);mn=int(a.min()) if a.size else 0;mx=int(a.max()) if a.size else 0
 dt=np.int16 if -32768<=mn and mx<=32767 else np.int32;code='<i2' if dt is np.int16 else '<i4';q=np.asarray(a,dtype=dt).ravel()
 dense=Z.compress(q.astype(code).tobytes());c=[('dense',len(dense),[dense])]
 nz=np.flatnonzero(q!=0).astype('<u4');v=q[nz].astype(code);ib=Z.compress(nz.tobytes());vb=Z.compress(v.tobytes());c.append(('sparse_idx',len(ib)+len(vb),[ib,vb]))
 mask=Z.compress(np.packbits((q!=0).astype(np.uint8),bitorder='little').tobytes());c.append(('bitmap',len(mask)+len(vb),[mask,vb]))
 mode,n,parts=min(c,key=lambda x:x[1])
 if mode=='dense':d=np.frombuffer(ZD.decompress(parts[0]),dtype=code).astype(dt)
 elif mode=='sparse_idx':
  ii=np.frombuffer(ZD.decompress(parts[0]),dtype='<u4');vv=np.frombuffer(ZD.decompress(parts[1]),dtype=code);d=np.zeros_like(q);d[ii]=vv
 else:
  mb=np.frombuffer(ZD.decompress(parts[0]),dtype=np.uint8);mk=np.unpackbits(mb,bitorder='little')[:q.size].astype(bool);vv=np.frombuffer(ZD.decompress(parts[1]),dtype=code);d=np.zeros_like(q);d[mk]=vv
 if not np.array_equal(d,q):raise RuntimeError(('pack',mode))
 return {'mode':mode,'bytes':n,'dtype':np.dtype(dt).str},d.reshape(a.shape)

def codec(X,eps,fr,irls=False):
 y,h,r,obj=solve(X,eps,fr)
 if irls:
  w=1.0/(np.abs(r.astype(np.float64)).ravel()+1.0);w=np.minimum(w,1000.0);y,h,r,obj=solve(X,eps,fr,w)
 # decoder boundary = first two time rows + left/right edge thereafter
 mask=np.zeros((NT,NX),bool);mask[:2,:]=True;mask[2:,0]=True;mask[2:,-1]=True;boundary=y[mask]
 pb,bd=exact_pack(boundary);ph,hd=exact_pack(h);pr,rd=exact_pack(r);total=FRAME+pb['bytes']+ph['bytes']+pr['bytes']
 p,q=fr.numerator,fr.denominator;yd=np.zeros_like(y);bi=0
 for t in range(NT):
  for x in range(NX):
   if t<2 or x==0 or x==NX-1:yd[t,x]=int(bd.ravel()[bi]);bi+=1
 for ti,t in enumerate(range(1,NT-1)):
  for xi,x in enumerate(range(1,NX-1)):
   # r = q*y[t+1] + (-2q+2p)y[t] + q*y[t-1] -p*(neighbors) - q*h
   num=int(rd[ti,xi])+q*int(hd[ti])-(-2*q+2*p)*int(yd[t,x])-q*int(yd[t-1,x])+p*int(yd[t,x+1])+p*int(yd[t,x-1])
   if num%q!=0:raise RuntimeError(('divisibility',str(fr),t,x,num,q))
   yd[t+1,x]=num//q
 if bi!=boundary.size or not np.array_equal(yd,y):raise RuntimeError(('decode',str(fr),bi,boundary.size,int(np.count_nonzero(yd!=y))))
 me=float(np.max(np.abs(X-yd.astype(np.float64))))
 if me>eps*(1+1e-12):raise RuntimeError(('hard',str(fr),me,eps))
 return {'lambda':float(fr),'fraction':f'{p}/{q}','irls':irls,'bytes':int(total),'bps':8*total/X.size,'maxerr':me,'defect_zero_fraction':float(np.mean(r==0)),'defect_mean_abs_scaled':float(np.mean(np.abs(r.astype(np.float64)))),'defect_std_scaled':float(np.std(r.astype(np.float64))),'boundary_bytes':pb['bytes'],'boundary_mode':pb['mode'],'shared_state_bytes':ph['bytes'],'shared_state_mode':ph['mode'],'defect_bytes':pr['bytes'],'defect_mode':pr['mode'],'lp_objective':obj}

def baseline(X,eps):
 old=(base.C,base.NT,base.TRAIN);base.C=NX;base.NT=NT;base.TRAIN=64
 try:
  _,co=base.fits(X.T);R,K=base.run_ar(X.T,co);ab,_,_,Kd=base.arithmetic(K);Rd=base.decode_source(Kd,co)
  if not np.array_equal(Rd,R):raise RuntimeError('AR replay');ame=float(np.max(np.abs(X.T-Rd.astype(np.float64))))
 finally:base.C,base.NT,base.TRAIN=old
 sz,_=base.m.szrun(np.ascontiguousarray(X.T.astype(np.float32)),eps)
 return {'ar32_bytes':int(ab),'ar32_bps':8*ab/X.size,'ar32_maxerr':ame,'sz3_bytes':int(sz),'sz3_bps':8*int(sz)/X.size}

def main(path):
 with h5py.File(path,'r') as f:
  ds=f['Acoustic'];_,std=base.m.stats(ds);eps=.1*std;rows=[];print(json.dumps({'std':std,'eps':eps,'tile':[NT,NX]}),flush=True)
  for region,c0 in REGIONS:
   X=np.asarray(ds[:NT,c0:c0+NX],np.int32);b=baseline(X,eps);cand=[]
   for n in LAM_NUMS:
    fr=frac_for(n);z=codec(X,eps,fr,False);z.update({'region':region,'c0':c0,**b,'gain_vs_ar32':b['ar32_bytes']/z['bytes'],'gain_vs_sz3':b['sz3_bytes']/z['bytes']});cand.append(z);print(json.dumps(z),flush=True)
   for z0 in sorted(cand,key=lambda z:z['bytes'])[:3]:
    fr=Fraction(z0['fraction']);z=codec(X,eps,fr,True);z.update({'region':region,'c0':c0,**b,'gain_vs_ar32':b['ar32_bytes']/z['bytes'],'gain_vs_sz3':b['sz3_bytes']/z['bytes']});cand.append(z);print(json.dumps(z),flush=True)
   rows+=cand;print(json.dumps({'region_summary':region,'baseline':b,'best':min(cand,key=lambda z:z['bytes']),'sparsest':max(cand,key=lambda z:z['defect_zero_fraction'])},indent=2),flush=True)
 json.dump({'global_std':std,'eps':eps,'tile':[NT,NX],'rows':rows,'scope':'Exact reconstructable field test of the original compression-resonance second-order wave annihilator. The entire DAS tile is jointly moved inside exact public hard-error boxes to minimize |A_lambda y-h(t)|. lambda is a fixed rational sweep. After legal integer projection, the shared forcing h is selected exactly and the scaled integer defect is serialized with boundary and h. Decoder receives only lambda plus those streams and recursively regenerates every interior sample using exact integer divisibility; all components are Zstd byte-round-tripped and max error verified. Best three byte candidates receive IRL1 refinement. Small-tile gate only.'},open('imperial_resonance_wave_quotient_fastgate.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
