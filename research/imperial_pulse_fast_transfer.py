import json,sys
import h5py,numpy as np,zstandard as zstd
sys.path.insert(0,__file__.rsplit('/',1)[0])
import imperial_huber_ar32_coldstart_arithmetic_regions as base
C=128;NT=30000;TB=1024;FRAME=98
REGIONS=(('hard',512),('easy',2304))
MS=(8,12,16,24,32,40,52,64,80,96,128,160,192,224,256,320,384,512)
Z=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()
def dtype_for(a):
 a=np.asarray(a);mn=int(a.min());mx=int(a.max());return np.dtype('<i2') if mn>=-32768 and mx<=32767 else np.dtype('<i4')
def interpolate(A,idx,eps):
 Ad=A.astype(np.float64)*eps;P=np.empty((C,NT),np.float64)
 for j in range(len(idx)-1):
  a,b=int(idx[j]),int(idx[j+1]);L=b-a;u=np.arange(L,dtype=np.float64)/float(L);P[:,a:b]=Ad[:,j,None]*(1-u)[None,:]+Ad[:,j+1,None]*u[None,:]
 P[:,-1]=Ad[:,-1];return P
def enc_candidate(X,eps,M,audit=False):
 idx=np.arange(0,NT,M,dtype=np.int32)
 if idx[-1]!=NT-1:idx=np.r_[idx,NT-1]
 A=np.rint(X[:,idx]/eps).astype(np.int32);P=interpolate(A,idx,eps);Cq=np.rint((X-P)/(2*eps)).astype(np.int32);R=P+Cq.astype(np.float64)*(2*eps);me=float(np.max(np.abs(X-R)))
 if me>eps*(1+1e-10):raise RuntimeError(('hard',M,me,eps))
 DA=A.copy();DA[:,1:]-=A[:,:-1];adt=dtype_for(A);dadt=dtype_for(DA);arb=Z.compress(np.ascontiguousarray(A).astype(adt).tobytes());adb=Z.compress(np.ascontiguousarray(DA).astype(dadt).tobytes());
 if len(adb)<len(arb):an='dA';ablob=adb;AQ=DA;adt2=dadt
 else:an='A';ablob=arb;AQ=A;adt2=adt
 K=Cq.copy();K[:,1:]-=Cq[:,:-1];kdt=dtype_for(K);kblob=Z.compress(np.ascontiguousarray(K).astype(kdt).tobytes())
 total=FRAME+len(ablob)+len(kblob)+1
 out={'M':M,'bytes':int(total),'bps':8*total/X.size,'anchor_bytes':len(ablob),'correction_bytes':len(kblob),'anchor_rep':an,'anchor_dtype':adt2.str,'correction_dtype':kdt.str,'anchors_per_channel':int(len(idx)),'transition_fraction':float(np.count_nonzero(K))/K.size,'state_zero_fraction':float(np.mean(Cq==0)),'state_std':float(np.std(Cq.astype(np.float64))),'maxerr':me}
 if audit:
  Adc=np.frombuffer(ZD.decompress(ablob),dtype=adt2,count=AQ.size).astype(np.int32).reshape(AQ.shape)
  if an=='dA':
   AA=Adc.copy();AA[:,1:]=Adc[:,0:1]+np.cumsum(Adc[:,1:],axis=1,dtype=np.int64)
  else:AA=Adc
  if not np.array_equal(AA,A):raise RuntimeError(('anchor decode',M))
  KD=np.frombuffer(ZD.decompress(kblob),dtype=kdt,count=K.size).astype(np.int32).reshape(K.shape);CD=np.cumsum(KD,axis=1,dtype=np.int64).astype(np.int32)
  if not np.array_equal(CD,Cq):raise RuntimeError(('correction decode',M))
  Pd=interpolate(AA,idx,eps);Rd=Pd+CD.astype(np.float64)*(2*eps)
  if not np.array_equal(Rd,R):raise RuntimeError(('replay',M))
  dme=float(np.max(np.abs(X-Rd)));out['decoded_maxerr']=dme;out['audit']='anchor bytes decoded; transition bytes decoded; correction state integrated; source regenerated exactly.'
 return out
def sz3(X,eps):
 n=0;me=0.
 for t0 in range(0,NT,TB):z,e=base.m.szrun(X[:,t0:min(t0+TB,NT)],eps);n+=int(z);me=max(me,float(e))
 return {'bytes':int(n),'bps':8*n/X.size,'maxerr':me}
def main(path):
 with h5py.File(path,'r') as f:
  ds=f['Acoustic'];_,std=base.m.stats(ds);eps=.1*std;rows=[];print(json.dumps({'std':std,'eps':eps}),flush=True)
  for region,c0 in REGIONS:
   X=np.asarray(ds[:NT,c0:c0+C],np.float64).T;sz=sz3(X,eps);cand=[]
   for M in MS:
    q=enc_candidate(X,eps,M,False);q['gain_vs_sz3']=sz['bytes']/q['bytes'];cand.append(q);print(json.dumps({'region':region,**q}),flush=True)
   best=min(cand,key=lambda q:q['bytes']);aud=enc_candidate(X,eps,best['M'],True);aud['gain_vs_sz3']=sz['bytes']/aud['bytes'];row={'region':region,'c0':c0,'samples':int(X.size),'sz3':sz,'best':aud,'candidates':cand};rows.append(row);print(json.dumps({'region_summary':row},indent=2),flush=True)
 json.dump({'std':std,'eps':eps,'rows':rows,'scope':'Fast exact transfer of PR29 PULSE to full 128x30000 Imperial hard/easy blocks. Public M sweep is selected by actual stream bytes and one selector byte is charged. Stream is the original mechanism: epsilon-quantized sparse anchors, linear interpolation, 2epsilon correction states, temporal first-difference correction transitions, Zstd. Best stream is independently byte-decoded and exact source reconstruction/max-error audited. Matched tiled SZ3 reruns on identical samples.'},open('imperial_pulse_fast_transfer.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
