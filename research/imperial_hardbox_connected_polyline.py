import json,sys,struct
import h5py,numpy as np
import imperial_hardbox_trajectory_codec as b

SCALES=(1,4,16,64,256)


def scaled_intervals(x,eps,S):
 lo=np.ceil((np.asarray(x,np.float64)-eps)*S).astype(np.int64)
 hi=np.floor((np.asarray(x,np.float64)+eps)*S).astype(np.int64)
 if np.any(lo>hi):raise RuntimeError(('empty scaled box',S))
 return lo,hi

def poly_segments(x,eps,S):
 lo,hi=scaled_intervals(x,eps,S);n=len(x)
 p0=int(np.rint(float(x[0])*S));p0=max(int(lo[0]),min(int(hi[0]),p0))
 p=p0;s=0;prevq=0;dts=[];qs=[]
 while s<n-1:
  qlo=-(1<<62);qhi=(1<<62);e=s+1
  while e<n:
   dt=e-s
   nqlo=max(qlo,b.ceildiv(int(lo[e])-p,dt))
   nqhi=min(qhi,(int(hi[e])-p)//dt)
   if nqlo>nqhi:break
   qlo,qhi=nqlo,nqhi;e+=1
  dt=e-s-1
  if dt<1:raise RuntimeError(('no next support',S,s,p,int(lo[s+1]),int(hi[s+1])))
  q=max(qlo,min(qhi,prevq))
  dts.append(dt);qs.append(int(q));p+=int(q)*dt;s+=dt;prevq=int(q)
 return p0,np.asarray(dts,np.int64),np.asarray(qs,np.int64)

def encode(X,eps,S):
 counts=[];dts=[];p0s=[];q0s=[];dqs=[]
 for c in range(X.shape[0]):
  p0,D,Q=poly_segments(X[c],eps,S);counts.append(len(D));dts.extend(D.tolist());p0s.append(p0);q0s.append(int(Q[0]))
  if len(Q)>1:dqs.extend(np.diff(Q).tolist())
 fs=[b.frame(counts),b.frame(dts),b.frame(p0s),b.frame(q0s),b.frame(dqs)]
 stream=struct.pack('<4sBIIII',b'PLY1',2,X.shape[0],X.shape[1],S,len(fs))+b''.join(struct.pack('<I',len(x))+x for x in fs)
 off=21;arr=[]
 for _ in range(5):
  L=struct.unpack_from('<I',stream,off)[0];off+=4;arr.append(b._decode_frame(stream[off:off+L]));off+=L
 if off!=len(stream):raise RuntimeError('poly trailing')
 dc,ddt,dp0,dq0,ddq=arr;R=np.empty(X.shape,np.float64);di=qi=0
 for c in range(X.shape[0]):
  ns=int(dc[c]);p=int(dp0[c]);q=int(dq0[c]);t=0;R[c,0]=p/float(S)
  for j in range(ns):
   dt=int(ddt[di]);di+=1
   if j>0:q+=int(ddq[qi]);qi+=1
   k=np.arange(1,dt+1,dtype=np.float64);R[c,t+1:t+dt+1]=(float(p)+float(q)*k)/float(S)
   p+=q*dt;t+=dt
  if t!=X.shape[1]-1:raise RuntimeError(('poly length',S,c,t))
 if di!=len(ddt) or qi!=len(ddq):raise RuntimeError('poly parse')
 me=float(np.max(np.abs(X-R)))
 if me>eps*(1+1e-10):raise RuntimeError(('poly hard',S,me,eps))
 return {'kind':'connected_polyline','scale':S,'bytes':len(stream),'bps':8*len(stream)/X.size,'maxerr':me,'segments':int(len(dts)),'mean_step_span':float((X.size-X.shape[0])/len(dts)),'median_segments_per_channel':float(np.median(counts))}

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=b.m.stats(d);eps=.1*gstd;rows=[]
  for region,c0 in b.SPECS:
   X=np.asarray(d[:b.NT,c0:c0+b.C],np.float64).T;rr=[]
   for S in SCALES:
    r=encode(X,eps,S);r.update({'region':region,'c0':c0,'ar32_bytes':b.BASE[region]['ar32_bytes'],'sz3_bytes':b.BASE[region]['sz3_bytes'],'gain_vs_ar32':b.BASE[region]['ar32_bytes']/r['bytes'],'gain_vs_sz3':b.BASE[region]['sz3_bytes']/r['bytes']});rr.append(r);print(json.dumps(r),flush=True)
   best=min(rr,key=lambda x:x['bytes']);rows.append({'region':region,'best':best,'all':rr})
  out={'global_std':gstd,'eps':eps,'shape':[b.C,b.NT],'scales':list(SCALES),'controls':'Pinned PR420 same-object AR32/SZ3 controls.','rows':rows,'scope':'Decoder-real connected hard-box polyline codec. Each channel stores one initial fixed-point support value. A segment maintains the complete integer slope interval whose line from the current support lies inside every subsequent +/-epsilon source box; points are greedily added until this slope interval would become empty. The chosen legal slope is nearest the previous slope, the segment endpoint becomes the next segment start exactly, and therefore no new anchor is transmitted. The actual stream contains per-channel segment counts, durations, initial supports, initial slopes and slope deltas only, each in a literal framed Zstd integer representation. Byte decode regenerates every support and every sample and independently verifies the unchanged source-domain hard error. This is the connected error-cone form of hard-box trajectory simplification, not a residual or post-hoc repair.'}
  json.dump(out,open('imperial_hardbox_connected_polyline.json','w'),indent=2)
  print(json.dumps({'summary':[{'region':x['region'],'bytes':x['best']['bytes'],'bps':x['best']['bps'],'scale':x['best']['scale'],'gain_ar32':x['best']['gain_vs_ar32'],'gain_sz3':x['best']['gain_vs_sz3'],'mean_span':x['best']['mean_step_span']} for x in rows]},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])