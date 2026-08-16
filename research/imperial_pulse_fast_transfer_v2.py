import json,sys
import h5py,numpy as np,zstandard as zstd
sys.path.insert(0,__file__.rsplit('/',1)[0])
import imperial_huber_ar32_coldstart_arithmetic_regions as base
C=128;NT=30000;TB=1024;FRAME=98
REGIONS=(('hard',512),('easy',2304));MS=(8,12,16,24,32,40,52,64,80,96,128,160,192,224,256,320,384,512)
Z=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()
def dtype_for(a):
 a=np.asarray(a);mn=int(a.min());mx=int(a.max());return np.dtype('<i2') if mn>=-32768 and mx<=32767 else np.dtype('<i4')
def interpolate(A,idx,eps):
 Ad=A.astype(np.float64)*eps;P=np.empty((C,NT),np.float64)
 for j in range(len(idx)-1):
  a,b=int(idx[j]),int(idx[j+1]);L=b-a;u=np.arange(L,dtype=np.float64)/float(L);P[:,a:b]=Ad[:,j,None]*(1-u)[None,:]+Ad[:,j+1,None]*u[None,:]
 P[:,-1]=Ad[:,-1];return P
def enc(X,eps,M,audit=False):
 idx=np.arange(0,NT,M,dtype=np.int32)
 if idx[-1]!=NT-1:idx=np.r_[idx,NT-1]
 A=np.rint(X[:,idx]/eps).astype(np.int32);P=interpolate(A,idx,eps);Cq=np.rint((X-P)/(2*eps)).astype(np.int32);R=P+Cq.astype(np.float64)*(2*eps);me=float(np.max(np.abs(X-R)))
 if me>eps*(1+1e-10):raise RuntimeError(('hard',M,me,eps))
 DA=A.copy();DA[:,1:]-=A[:,:-1]
 opts=[]
 for name,Q in [('A',A),('dA',DA)]:
  dt=dtype_for(Q);bb=Z.compress(np.ascontiguousarray(Q).astype(dt).tobytes());opts.append((len(bb),name,Q,dt,bb))
 _,an,AQ,adt,ab=min(opts,key=lambda z:z[0])
 K=Cq.copy();K[:,1:]-=Cq[:,:-1];kdt=dtype_for(K);kb=Z.compress(np.ascontiguousarray(K).astype(kdt).tobytes());total=FRAME+len(ab)+len(kb)+1
 out={'M':M,'bytes':int(total),'bps':8*total/X.size,'anchor_bytes':len(ab),'correction_bytes':len(kb),'anchor_rep':an,'anchor_dtype':adt.str,'correction_dtype':kdt.str,'anchors_per_channel':int(len(idx)),'transition_fraction':float(np.count_nonzero(K))/K.size,'state_zero_fraction':float(np.mean(Cq==0)),'state_std':float(np.std(Cq.astype(np.float64))),'maxerr':me}
 if audit:
  AQd=np.frombuffer(ZD.decompress(ab),dtype=adt,count=AQ.size).astype(np.int32).reshape(AQ.shape)
  if an=='dA':AA=AQd.copy();AA[:,1:]=AQd[:,0:1]+np.cumsum(AQd[:,1:],axis=1,dtype=np.int64)
  else:AA=AQd
  KD=np.frombuffer(ZD.decompress(kb),dtype=kdt,count=K.size).astype(np.int32).reshape(K.shape);CD=np.cumsum(KD,axis=1,dtype=np.int64).astype(np.int32)
  if not np.array_equal(AA,A) or not np.array_equal(CD,Cq):raise RuntimeError(('decode',M))
  Rd=interpolate(AA,idx,eps)+CD.astype(np.float64)*(2*eps)
  if not np.array_equal(Rd,R):raise RuntimeError(('replay',M))
  out['decoded_maxerr']=float(np.max(np.abs(X-Rd)));out['audit']='byte-decoded anchors and correction transitions; exact correction integration and source replay.'
 return out
def sz3(X,eps):
 n=0
 for t0 in range(0,NT,TB):
  ret=base.m.szrun(X[:,t0:min(t0+TB,NT)],eps);n+=int(ret[0])
 return {'bytes':int(n),'bps':8*n/X.size}
def main(path):
 with h5py.File(path,'r') as f:
  ds=f['Acoustic'];_,std=base.m.stats(ds);eps=.1*std;rows=[];print(json.dumps({'std':std,'eps':eps}),flush=True)
  for region,c0 in REGIONS:
   X=np.asarray(ds[:NT,c0:c0+C],np.float64).T;sz=sz3(X,eps);cand=[]
   for M in MS:
    q=enc(X,eps,M);q['gain_vs_sz3']=sz['bytes']/q['bytes'];cand.append(q);print(json.dumps({'region':region,**q}),flush=True)
   best=min(cand,key=lambda q:q['bytes']);aud=enc(X,eps,best['M'],True);aud['gain_vs_sz3']=sz['bytes']/aud['bytes'];row={'region':region,'c0':c0,'samples':int(X.size),'sz3':sz,'best':aud,'candidates':cand};rows.append(row);print(json.dumps({'region_summary':row},indent=2),flush=True)
 json.dump({'std':std,'eps':eps,'rows':rows,'scope':'Exact PR29 PULSE transfer on full Imperial hard/easy 128x30000 blocks. Actual public M sweep, selector charged, original anchor/interpolation/2epsilon correction-transition mechanism, exact Zstd byte roundtrip and source replay; matched tiled SZ3 on identical samples.'},open('imperial_pulse_fast_transfer_v2.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
