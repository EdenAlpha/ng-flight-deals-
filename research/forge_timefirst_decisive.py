import json,numpy as np,zstandard as zstd
m=json.load(open('data/forge_subcube_meta.json'));eps=float(m['eps_10pct_std']);X=np.fromfile('data/forge_subcube_f32.bin','<f4').reshape(64,64,512).astype(np.float32);R=np.fromfile('diagnostic_rec.bin','<f4').reshape(64,64,512).astype(np.float32);Z=zstd.ZstdCompressor(level=19)
def h(a):
 _,c=np.unique(a,return_counts=True);p=c/c.sum();return float(-(p*np.log2(p)).sum())
def met(Y,P,mb=0):
 q=np.rint((Y.astype(float)-P.astype(float))/(2*eps)).astype(np.int16);rec=P.astype(float)+q*(2*eps);lo,hi=int(q.min()),int(q.max());dt=np.int8 if lo>=-128 and hi<=127 else np.int16;raw=len(Z.compress(q.astype(dt).tobytes()));nz=q!=0;mv=len(Z.compress(np.packbits(nz,bitorder='little').tobytes()+q[nz].astype(dt).tobytes()));b=min(raw,mv)+mb;return {'bytes':b,'stream':b-mb,'model':mb,'zero':float(np.mean(q==0)),'H':h(q),'maxerr':float(np.max(np.abs(Y-rec)))}
def grid(k):
 if k=='x':
  I=np.arange(1,62,2);J=np.arange(0,64,2);return X[I[:,None],J[None,:]],R[(I-1)[:,None],J[None,:]],R[(I+1)[:,None],J[None,:]]
 I=np.arange(0,64,2);J=np.arange(1,62,2);return X[I[:,None],J[None,:]],R[I[:,None],(J-1)[None,:]],R[I[:,None],(J+1)[None,:]]
def ana(a):
 N=a.shape[-1];F=np.fft.fft(a.astype(float),axis=-1);w=np.zeros(N);w[0]=w[N//2]=1;w[1:N//2]=2;return np.fft.ifft(F*w,axis=-1)
def phase(L,Rr,geom):
 z1=ana(L);z2=ana(Rr);d=np.unwrap(np.angle(z2*np.conj(z1)),axis=-1);ph=np.unwrap(np.angle(z1),axis=-1)+.5*d;amp=np.sqrt(np.abs(z1)*np.abs(z2)) if geom else .5*(np.abs(z1)+np.abs(z2));return (amp*np.exp(1j*ph)).real.astype(np.float32)
def local(Y,L,Rr,tile,rad):
 P=.5*(L+Rr);co=0;v=np.arange(rad,512-rad)
 for a in range(0,Y.shape[0],tile):
  for b in range(0,Y.shape[1],tile):
   ss=(slice(a,min(a+tile,Y.shape[0])),slice(b,min(b+tile,Y.shape[1])));y=Y[ss];l=L[ss];r=Rr[ss];cols=[]
   for d in range(-rad,rad+1):cols += [(.5*(l[...,v+d]+r[...,v+d])).reshape(-1),(.5*(r[...,v+d]-l[...,v+d])).reshape(-1)]
   cols.append(np.ones(y.shape[0]*y.shape[1]*len(v)));A=np.stack(cols,1).astype(float);yy=y[...,v].reshape(-1).astype(float);G=A.T@A;rhs=A.T@yy;lam=1e-8*np.trace(G)/G.shape[0];reg=np.eye(G.shape[0])*lam;reg[-1,-1]=0;w=np.linalg.solve(G+reg,rhs).astype(np.float32);P[ss][...,v]=(A.astype(np.float32)@w).reshape(y.shape[0],y.shape[1],-1);co+=len(w)
 return P,4*co+64
rows=[]
for k in ['x','y']:
 Y,L,Rr=grid(k);rows.append({'axis':k,'method':'avg','m':met(Y,.5*(L+Rr),32)})
 for g in [False,True]:rows.append({'axis':k,'method':'analytic_geom' if g else 'analytic_arith','m':met(Y,phase(L,Rr,g),32)})
 for tile,rad in [(8,8),(4,8),(8,4)]:
  P,mb=local(Y,L,Rr,tile,rad);rows.append({'axis':k,'method':f'fir_t{tile}_r{rad}','m':met(Y,P,mb)})
print(json.dumps(rows,indent=2));json.dump({'eps':eps,'rows':rows},open('forge_timefirst_decisive.json','w'),indent=2)
