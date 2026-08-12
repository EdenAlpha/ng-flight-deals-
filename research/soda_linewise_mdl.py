import sys,json,os,struct,numpy as np,segyio
from collections import Counter
src=open('research/soda_linewise_topn.py').read().split('\ndef main(path):')[0]
exec(compile(src,'soda_linewise_topn.py','exec'),globals())
FC={}
def encode_N(X,eps,B,N):
 nr,nt=X.shape;nblk=(nt+B-1)//B;key=(id(X),B);specs=FC.get(key)
 if specs is None:
  specs=[]
  for b in range(nblk):
   t0=b*B;m=min(B,nt-t0);W=np.zeros((nr,B),np.float32);W[:,:m]=X[:,t0:t0+m];specs.append((fwd(W),m))
  FC[key]=specs
 step=2*eps;P=np.zeros_like(X);idxs=[];vals=[];scs=[]
 if N>0:
  for b,(F,m) in enumerate(specs):
   flat=F.ravel();nn=min(N,flat.size);ix=np.argpartition(np.abs(flat),-nn)[-nn:];ix=np.sort(ix).astype(np.uint32);v=flat[ix];cp=np.stack([v.real,v.imag],1);s16=np.float16(max(float(np.max(np.abs(cp)))/127,1e-30));sd=np.float32(s16);q=np.clip(np.rint(cp/sd),-127,127).astype(np.int8);fq=np.zeros(flat.size,np.complex64);fq[ix.astype(np.int64)]=(q[:,0].astype(np.float32)+1j*q[:,1].astype(np.float32))*sd;t0=b*B;R=inv(fq.reshape(F.shape),B);P[:,t0:t0+m]=R[:,:m];idxs.append(ix);vals.append(q);scs.append(s16)
  iz=z(np.concatenate(idxs).astype('<u4',copy=False).tobytes());vz=z(np.concatenate(vals).astype(np.int8,copy=False).tobytes());szb=z(np.asarray(scs,dtype='<f2').tobytes())
 else: iz=vz=szb=b''
 Q=np.rint((X-P)/step).astype(np.int32);opts=[];dc,a=pack_int(Q);opts.append((len(a),0,dc,a,b''));K=Q.copy();K[:,1:]-=Q[:,:-1];dc,a=pack_int(K);opts.append((len(a),1,dc,a,b''));mask=K!=0;mz=z(np.packbits(mask.ravel(),bitorder='little').tobytes());dc,vv=pack_int(K[mask]);opts.append((len(mz)+len(vv),2,dc,mz,vv));_,cm,dc,ca,cb=min(opts,key=lambda x:x[0]);h=struct.pack(PH,nr,nt,B,N,nblk,cm,dc,len(iz),len(vz),len(szb),len(ca),len(cb));return h+iz+vz+szb+ca+cb,float(mask.mean()),P

def decode_N(blob,eps):
 nr,nt,B,N,nblk,cm,dc,*lens=struct.unpack(PH,blob[:PHS]);p=PHS;ss=[]
 for L in lens:ss.append(blob[p:p+L]);p+=L
 iz,vz,szb,ca,cb=ss;P=np.zeros((nr,nt),np.float32)
 if N>0:
  cnt=nblk*N;ix=np.frombuffer(D.decompress(iz),dtype='<u4',count=cnt);q=np.frombuffer(D.decompress(vz),dtype=np.int8,count=2*cnt).reshape(cnt,2);sc=np.frombuffer(D.decompress(szb),dtype='<f2',count=nblk);shape=(nr,B//2+1);M=int(np.prod(shape))
  for b in range(nblk):
   sl=slice(b*N,(b+1)*N);F=np.zeros(M,np.complex64);F[ix[sl].astype(np.int64)]=(q[sl,0].astype(np.float32)+1j*q[sl,1].astype(np.float32))*np.float32(sc[b]);R=inv(F.reshape(shape),B);t0=b*B;m=min(B,nt-t0);P[:,t0:t0+m]=R[:,:m]
 total=nr*nt
 if cm==0:Q=unpack_int(ca,dc,total).reshape(nr,nt)
 elif cm==1:Q=np.cumsum(unpack_int(ca,dc,total).reshape(nr,nt),axis=1,dtype=np.int32)
 else:
  mask=np.unpackbits(np.frombuffer(D.decompress(ca),np.uint8),bitorder='little',count=total).astype(bool);vv=unpack_int(cb,dc,int(mask.sum()));K=np.zeros(total,np.int32);K[mask]=vv;Q=np.cumsum(K.reshape(nr,nt),axis=1,dtype=np.int32)
 return P+Q.astype(np.float32)*np.float32(2*eps)

path=sys.argv[1]
with segyio.open(path,'r',ignore_geometry=True) as f:X=np.asarray(f.trace.raw[:],np.float32).copy();gx=np.asarray(f.attributes(segyio.TraceField.GroupX)[:],np.int64);gy=np.asarray(f.attributes(segyio.TraceField.GroupY)[:],np.int64)
eps=.1*float(X.astype(np.float64).std());raw=X.nbytes;panels,out,meta,geom=partition(X,gx,gy);fb,fe=sz3(X,eps);outb=b'';outerr=0
if out.size:outb,outerr=sz3(out,eps)
rows=[]
for B in [256,512,1024]:
 chosen=[];total=len(outb)+struct.calcsize('<8sdIIQ')+8*len(panels);mx=outerr;wev=0;wn=0
 for pi,p in enumerate(panels):
  candidates=[]
  for N in [0,1,2,4,6,8,12,16,24,32]:
   ch,ev,_=encode_N(p,eps,B,N);candidates.append((len(ch),N,ch,ev))
  ln,N,ch,ev=min(candidates,key=lambda x:x[0]);R=decode_N(ch,eps);er=float(np.max(np.abs(p-R)));mx=max(mx,er);total+=ln;wev+=ev*p.size;wn+=p.size;chosen.append({'panel':pi,'N':N,'bytes':ln,'event_fraction':ev})
 dist=dict(Counter(q['N'] for q in chosen));row={'B':B,'bytes':total,'ratio':raw/total,'maxerr':mx,'valid':bool(mx<=eps*(1+3e-6)),'event_fraction':wev/wn,'chosen_N_distribution':dist,'outlier_bytes':len(outb)};rows.append(row);print('MDL',json.dumps(row),flush=True);FC.clear()
rows.sort(key=lambda r:r['ratio'],reverse=True);res={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'eps':eps,'geometry':geom,'top':rows,'sz3_file':{'bytes':len(fb),'ratio':raw/len(fb),'maxerr':fe}};json.dump(res,open('soda_linewise_mdl.json','w'),indent=2);print('BEST',json.dumps({'codec':rows[0],'sz3':res['sz3_file']},indent=2))
