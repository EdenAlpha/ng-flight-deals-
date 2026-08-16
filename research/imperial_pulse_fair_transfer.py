import json,sys,math
import h5py,numpy as np,zstandard as zstd
sys.path.insert(0,__file__.rsplit('/',1)[0])
import imperial_huber_ar32_coldstart_arithmetic_regions as base

C=128;NT=30000;TB=1024;FRAME=96
REGIONS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
MS=(8,12,16,24,32,40,52,64,80,96,128,160,192,224,256,320,384,512)
Z=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()

def dtype_for(a):
 a=np.asarray(a);mn=int(a.min()) if a.size else 0;mx=int(a.max()) if a.size else 0
 if -32768<=mn and mx<=32767:return np.dtype('<i2')
 return np.dtype('<i4')
def pack(a):
 a=np.asarray(a);dt=dtype_for(a);b=Z.compress(np.ascontiguousarray(a).astype(dt).tobytes());d=np.frombuffer(ZD.decompress(b),dtype=dt,count=a.size).astype(np.int32).reshape(a.shape)
 if not np.array_equal(d,a.astype(np.int32)):raise RuntimeError('pack')
 return b,d,dt.str

def pulse(X,eps,M):
 idx=np.arange(0,NT,M,dtype=np.int32)
 if idx[-1]!=NT-1:idx=np.r_[idx,NT-1]
 A=np.rint(X[:,idx]/eps).astype(np.int32)
 Ad=A.astype(np.float64)*eps
 P=np.empty_like(X,np.float64)
 for j in range(len(idx)-1):
  a,b=int(idx[j]),int(idx[j+1]);L=b-a;u=np.arange(L,dtype=np.float64)/float(L);P[:,a:b]=Ad[:,j,None]*(1-u)[None,:]+Ad[:,j+1,None]*u[None,:]
 P[:,-1]=Ad[:,-1]
 Cc=np.rint((X-P)/(2*eps)).astype(np.int32)
 R=P+Cc.astype(np.float64)*(2*eps)
 me=float(np.max(np.abs(X-R)))
 if me>eps*(1+1e-10):raise RuntimeError(('hard',M,me,eps))
 # Exact reversible byte languages for anchors and correction states.
 DA=A.copy();DA[:,1:]-=A[:,:-1]
 anchor=[]
 for name,Q in [('A',A),('dA',DA)]:
  bb,dd,dt=pack(Q);anchor.append((len(bb),name,bb,dd,dt))
 ab,an,ablob,Aenc,adt=min(anchor,key=lambda z:z[0])
 if an=='dA':
  Adec=Aenc.copy();Adec[:,1:]=np.cumsum(Adec[:,1:],axis=1)+Adec[:,0:1]
 else:Adec=Aenc
 if not np.array_equal(Adec,A):raise RuntimeError(('A decode',M))
 K=Cc.copy();K[:,1:]-=Cc[:,:-1]
 SD=Cc.copy();SD[1:]-=Cc[:-1]
 LZ=Cc.copy();LZ[1:,1:]=Cc[1:,1:]-Cc[1:,:-1]-Cc[:-1,1:]+Cc[:-1,:-1]
 reps=[]
 for name,Q in [('C',Cc),('dT',K),('dX',SD),('lorenzo',LZ)]:
  bb,dd,dt=pack(Q);reps.append((len(bb),name,bb,dd,dt))
 cb,cn,cblob,Cenc,cdt=min(reps,key=lambda z:z[0])
 if cn=='dT': Cdec=np.cumsum(Cenc,axis=1,dtype=np.int64).astype(np.int32)
 elif cn=='dX': Cdec=np.cumsum(Cenc,axis=0,dtype=np.int64).astype(np.int32)
 elif cn=='lorenzo':
  Cdec=np.empty_like(Cenc);Cdec[0,0]=Cenc[0,0]
  for t in range(1,NT):Cdec[0,t]=Cenc[0,t]+Cdec[0,t-1]
  for c in range(1,C):Cdec[c,0]=Cenc[c,0]+Cdec[c-1,0]
  for c in range(1,C):
   for t in range(1,NT):Cdec[c,t]=Cenc[c,t]+Cdec[c,t-1]+Cdec[c-1,t]-Cdec[c-1,t-1]
 else:Cdec=Cenc
 if not np.array_equal(Cdec,Cc):raise RuntimeError(('C decode',M,cn))
 # Independent reconstruction from decoded A/C and public M/eps.
 Ad2=Adec.astype(np.float64)*eps;Pd=np.empty_like(X,np.float64)
 for j in range(len(idx)-1):
  a,b=int(idx[j]),int(idx[j+1]);L=b-a;u=np.arange(L,dtype=np.float64)/float(L);Pd[:,a:b]=Ad2[:,j,None]*(1-u)[None,:]+Ad2[:,j+1,None]*u[None,:]
 Pd[:,-1]=Ad2[:,-1];Rd=Pd+Cdec.astype(np.float64)*(2*eps)
 if not np.array_equal(Rd,R):raise RuntimeError(('R replay',M))
 dme=float(np.max(np.abs(X-Rd)))
 total=FRAME+ab+cb+2 # public candidate index + representation selectors, conservatively 2 bytes
 return {'M':M,'bytes':int(total),'bps':8*total/X.size,'anchor_bytes':int(ab),'anchor_rep':an,'anchor_dtype':adt,'correction_bytes':int(cb),'correction_rep':cn,'correction_dtype':cdt,'anchors_per_channel':int(len(idx)),'correction_transition_fraction':float(np.count_nonzero(K))/K.size,'correction_zero_fraction':float(np.mean(Cc==0)),'correction_std':float(np.std(Cc.astype(np.float64))),'maxerr':dme}

def ar32(X,eps):
 old=(base.C,base.NT,base.TRAIN);base.C=C;base.NT=NT;base.TRAIN=1024
 try:
  _,co=base.fits(X);R,K=base.run_ar(X,co);bb,_,_,Kd=base.arithmetic(K);Rd=base.decode_source(Kd,co)
  if not np.array_equal(Rd,R):raise RuntimeError('ar replay');me=float(np.max(np.abs(X-Rd.astype(np.float64))))
 finally:base.C,base.NT,base.TRAIN=old
 return {'bytes':int(bb),'bps':8*bb/X.size,'maxerr':me}
def sz3(X,eps):
 n=0;me=0.
 for t0 in range(0,NT,TB):
  z,e=base.m.szrun(X[:,t0:min(t0+TB,NT)],eps);n+=int(z);me=max(me,float(e))
 return {'bytes':int(n),'bps':8*n/X.size,'maxerr':me}

def main(path):
 base.C=C;base.NT=NT;base.TRAIN=1024
 with h5py.File(path,'r') as f:
  ds=f['Acoustic'];_,std=base.m.stats(ds);eps=.1*std;rows=[];print(json.dumps({'std':std,'eps':eps,'shape':list(ds.shape)}),flush=True)
  for region,c0 in REGIONS:
   X=np.asarray(ds[:NT,c0:c0+C],np.float64).T;az=ar32(X,eps);sz=sz3(X,eps);cand=[]
   for M in MS:
    q=pulse(X,eps,M);q.update({'gain_vs_ar32':az['bytes']/q['bytes'],'gain_vs_sz3':sz['bytes']/q['bytes']});cand.append(q);print(json.dumps({'region':region,**q}),flush=True)
   best=min(cand,key=lambda q:q['bytes']);row={'region':region,'c0':c0,'samples':int(X.size),'ar32':az,'sz3':sz,'best_pulse':best,'candidates':cand};rows.append(row);print(json.dumps({'region_summary':row},indent=2),flush=True)
 json.dump({'std':std,'eps':eps,'rows':rows,'scope':'Fair deployable PULSE transfer to the exact Imperial minute. Each full 128x30000 cable block uses sparse epsilon-quantized temporal anchors, linear interpolation, and exact 2epsilon correction states. Public M candidates are screened by actual fully charged bytes; one candidate/representation selector allowance is charged. Anchor and correction streams each choose only among exact reversible Zstd layouts and are byte-decoded. Full reconstruction is independently regenerated and hard-error verified. Matched Huber AR32 and tiled SZ3 rerun on identical samples. No Brady-specific M is assumed.'},open('imperial_pulse_fair_transfer.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
