import json,os,struct,sys
from collections import defaultdict
import numpy as np,segyio,zstandard as zstd
from pysz import sz,szConfig,szErrorBoundMode
C=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor();IDT={1:np.dtype('<i1'),2:np.dtype('<i2'),3:np.dtype('<i4')}
PH='<IIIIIBBQQQQQ';PHS=struct.calcsize(PH)

def z(b):return C.compress(b)
def pack_int(a):
 a=np.asarray(a);lo=int(a.min()) if a.size else 0;hi=int(a.max()) if a.size else 0;code=1 if lo>=-128 and hi<=127 else 2 if lo>=-32768 and hi<=32767 else 3;return code,z(np.ascontiguousarray(a.astype(IDT[code],copy=False)).tobytes())
def unpack_int(b,c,n):return np.frombuffer(D.decompress(b),dtype=IDT[c],count=n).astype(np.int32,copy=False)
def fwd(W):return np.fft.fft(np.fft.rfft(W,axis=1),axis=0)
def inv(F,B):return np.fft.irfft(np.fft.ifft(F,axis=0),n=B,axis=1).real.astype(np.float32)

def encode_panel(X,eps,B,frac):
 nr,nt=X.shape;nblk=(nt+B-1)//B;step=2*eps;idxs=[];vals=[];scs=[];P=np.zeros_like(X);N=None
 for b in range(nblk):
  t0=b*B;m=min(B,nt-t0);W=np.zeros((nr,B),np.float32);W[:,:m]=X[:,t0:t0+m];F=fwd(W);flat=F.ravel();NN=max(1,int(round(frac*flat.size)));N=NN if N is None else N;ix=np.argpartition(np.abs(flat),-N)[-N:];ix=np.sort(ix).astype(np.uint32);v=flat[ix];cp=np.stack([v.real,v.imag],1);s16=np.float16(max(float(np.max(np.abs(cp)))/127,1e-30));sd=np.float32(s16);q=np.clip(np.rint(cp/sd),-127,127).astype(np.int8);fq=np.zeros(flat.size,np.complex64);fq[ix.astype(np.int64)]=(q[:,0].astype(np.float32)+1j*q[:,1].astype(np.float32))*sd;R=inv(fq.reshape(F.shape),B);P[:,t0:t0+m]=R[:,:m];idxs.append(ix);vals.append(q);scs.append(s16)
 iz=z(np.concatenate(idxs).astype('<u4',copy=False).tobytes());vz=z(np.concatenate(vals).astype(np.int8,copy=False).tobytes());szb=z(np.asarray(scs,dtype='<f2').tobytes());Q=np.rint((X-P)/step).astype(np.int32);opts=[];dc,a=pack_int(Q);opts.append((len(a),0,dc,a,b''));K=Q.copy();K[:,1:]-=Q[:,:-1];dc,a=pack_int(K);opts.append((len(a),1,dc,a,b''));mask=K!=0;mz=z(np.packbits(mask.ravel(),bitorder='little').tobytes());dc,vv=pack_int(K[mask]);opts.append((len(mz)+len(vv),2,dc,mz,vv));_,cm,dc,ca,cb=min(opts,key=lambda x:x[0]);h=struct.pack(PH,nr,nt,B,N,nblk,cm,dc,len(iz),len(vz),len(szb),len(ca),len(cb));return h+iz+vz+szb+ca+cb,float(mask.mean())
def decode_panel(blob,eps):
 nr,nt,B,N,nblk,cm,dc,*lens=struct.unpack(PH,blob[:PHS]);p=PHS;ss=[]
 for L in lens:ss.append(blob[p:p+L]);p+=L
 iz,vz,szb,ca,cb=ss;cnt=nblk*N;ix=np.frombuffer(D.decompress(iz),dtype='<u4',count=cnt);q=np.frombuffer(D.decompress(vz),dtype=np.int8,count=2*cnt).reshape(cnt,2);sc=np.frombuffer(D.decompress(szb),dtype='<f2',count=nblk);P=np.zeros((nr,nt),np.float32);shape=(nr,B//2+1);M=np.prod(shape)
 for b in range(nblk):
  sl=slice(b*N,(b+1)*N);F=np.zeros(M,np.complex64);F[ix[sl].astype(np.int64)]=(q[sl,0].astype(np.float32)+1j*q[sl,1].astype(np.float32))*np.float32(sc[b]);R=inv(F.reshape(shape),B);t0=b*B;m=min(B,nt-t0);P[:,t0:t0+m]=R[:,:m]
 total=nr*nt
 if cm==0:Q=unpack_int(ca,dc,total).reshape(nr,nt)
 elif cm==1:Q=np.cumsum(unpack_int(ca,dc,total).reshape(nr,nt),axis=1,dtype=np.int32)
 else:
  mask=np.unpackbits(np.frombuffer(D.decompress(ca),np.uint8),bitorder='little',count=total).astype(bool);vv=unpack_int(cb,dc,int(mask.sum()));K=np.zeros(total,np.int32);K[mask]=vv;Q=np.cumsum(K.reshape(nr,nt),axis=1,dtype=np.int32)
 return P+Q.astype(np.float32)*np.float32(2*eps)
def sz3(X,eps):
 cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps);b,_=sz.compress(np.ascontiguousarray(X),cfg);R,_=sz.decompress(b,np.float32,X.shape);return bytes(b),float(np.max(np.abs(X-R)))

def partition(X,gx,gy):
 coord=defaultdict(list)
 for i,k in enumerate(zip(gx.tolist(),gy.tolist())):coord[k].append(i)
 pts=np.array(list(coord.keys()),dtype=float);keys=list(coord.keys());d=pts[:,None,:]-pts[None,:,:];ds=np.sum(d*d,2);ds[ds==0]=np.inf;j=np.argmin(ds,1);v=pts[j]-pts;v=np.where(((v[:,0]<0)|((v[:,0]==0)&(v[:,1]<0)))[:,None],-v,v);lens=np.linalg.norm(v,axis=1);sp=float(np.median(lens));vv=v[(lens>.5*sp)&(lens<1.5*sp)];u=np.median(vv,0);u=u/np.linalg.norm(u);perp=np.array([-u[1],u[0]]);a=pts@u;b=pts@perp;order=np.argsort(b);cuts=np.where(np.diff(b[order])>.2*sp)[0]+1;rawgroups=np.split(order,cuts);main=[g for g in rawgroups if len(g)>=10];main=sorted(main,key=lambda g:float(np.mean(b[g])));used=set();panels=[];meta=[]
 for li,g in enumerate(main):
  gg=sorted(g.tolist(),key=lambda q:a[q]);maxc=max(len(coord[keys[q]]) for q in gg)
  for c in range(maxc):
   ids=[coord[keys[q]][c] for q in gg if len(coord[keys[q]])>c]
   if len(ids)>=8:panels.append(X[np.array(ids)]);meta.append({'line':li,'component_rank':c,'traces':len(ids)});used.update(ids)
 outids=[i for i in range(X.shape[0]) if i not in used];return panels,X[np.array(outids)] if outids else np.empty((0,X.shape[1]),np.float32),meta,{'line_count':len(main),'main_receiver_sites':int(sum(len(g) for g in main)),'along_axis':u.tolist(),'along_spacing':sp,'outlier_traces':len(outids)}

def main(path):
 with segyio.open(path,'r',ignore_geometry=True) as f:X=np.asarray(f.trace.raw[:],np.float32).copy();gx=np.asarray(f.attributes(segyio.TraceField.GroupX)[:],np.int64);gy=np.asarray(f.attributes(segyio.TraceField.GroupY)[:],np.int64)
 eps=.1*float(X.astype(np.float64).std());raw=X.nbytes;panels,out,meta,geom=partition(X,gx,gy);fb,fe=sz3(X,eps);base=[{'kind':'file_sz3','bytes':len(fb),'ratio':raw/len(fb),'maxerr':fe}];lb=0;lerr=0
 for p in panels:
  b,e=sz3(p,eps);lb+=len(b);lerr=max(lerr,e)
 if out.size:b,e=sz3(out,eps);lb+=len(b);lerr=max(lerr,e)
 base.append({'kind':'linewise_sz3','bytes':lb,'ratio':raw/lb,'maxerr':lerr});rows=[]
 for B in [512,1024]:
  for frac in [.001,.002,.004,.008,.016]:
   chunks=[];events=[];maxe=0
   for p in panels:
    ch,ev=encode_panel(p,eps,B,frac);R=decode_panel(ch,eps);maxe=max(maxe,float(np.max(np.abs(p-R))));chunks.append(ch);events.append((ev,p.size))
   outb=b'';outerr=0
   if out.size:outb,outerr=sz3(out,eps);maxe=max(maxe,outerr)
   overhead=struct.calcsize('<8sdIIQ')+8*len(chunks);total=overhead+sum(len(q) for q in chunks)+len(outb);event=sum(e*w for e,w in events)/sum(w for _,w in events);row={'B':B,'frac':frac,'bytes':total,'ratio':raw/total,'event_fraction':event,'maxerr':maxe,'valid':bool(maxe<=eps*(1+3e-6)),'model_panels':len(chunks),'outlier_bytes':len(outb)};rows.append(row);print(json.dumps(row),flush=True)
 rows.sort(key=lambda r:r['ratio'],reverse=True);base.sort(key=lambda r:r['ratio'],reverse=True);res={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'eps':eps,'geometry':geom,'panel_meta':meta,'top':rows,'baselines':base};json.dump(res,open('soda_linewise_topn.json','w'),indent=2);print('BEST',json.dumps({'codec':rows[0],'baseline':base[0],'geometry':geom},indent=2))
main(sys.argv[1])
