import json,math,sys
import h5py,numpy as np,zstandard as zstd
from pysz import sz,szConfig,szErrorBoundMode

CB=128;TB=1024;SAFETY=1-1e-5;Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor()

def stats(d):
 s=ss=0.;n=0
 for i in range(0,d.shape[0],2048):
  x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
 m=s/n;return m,float(np.sqrt(max(0,ss/n-m*m)))

def szrun(X,eps):
 best=None
 for tr in (False,True):
  A=np.ascontiguousarray((X.T if tr else X).astype(np.float32));cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
  b,_=sz.compress(A,cfg);R,_=sz.decompress(b,np.float32,A.shape)
  me=float(np.max(np.abs(A-R)))
  if not math.isfinite(me) or me>eps*(1+5e-6):raise RuntimeError(('sz hard',me,eps))
  row=(int(b.size),'T' if tr else 'CT')
  if best is None or row[0]<best[0]:best=row
 return best

def sdtype(mn,mx):
 for dt in (np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4')):
  if mn>=np.iinfo(dt).min and mx<=np.iinfo(dt).max:return dt
 raise RuntimeError(('signed range',mn,mx))
def udtype(mx):
 for dt in (np.dtype('u1'),np.dtype('<u2'),np.dtype('<u4')):
  if mx<=np.iinfo(dt).max:return dt
 raise RuntimeError(('unsigned range',mx))

def enc_int(a):
 a=np.asarray(a,np.int32);flat=a.ravel();n=flat.size;c=[];mn=int(flat.min()) if n else 0;mx=int(flat.max()) if n else 0
 dt=sdtype(mn,mx);b=Z.compress(flat.astype(dt).tobytes());r=np.frombuffer(D.decompress(b),dt,count=n).astype(np.int32);c.append((len(b)+64,'signed_'+dt.str,r))
 zz=((flat.astype(np.int64)<<1)^(flat.astype(np.int64)>>63)).astype(np.uint64);mz=int(zz.max()) if n else 0;du=udtype(mz);b=Z.compress(zz.astype(du).tobytes());z=np.frombuffer(D.decompress(b),du,count=n).astype(np.uint64);r=((z>>1).astype(np.int64)^-(z&1).astype(np.int64)).astype(np.int32);c.append((len(b)+64,'zigzag_'+du.str,r))
 nz=flat!=0;pb=np.packbits(nz.astype(np.uint8),bitorder='little');sb=Z.compress(pb.tobytes());mask=np.unpackbits(np.frombuffer(D.decompress(sb),np.uint8),bitorder='little',count=n).astype(bool);v=flat[nz]
 if v.size:
  dv=sdtype(int(v.min()),int(v.max()));vb=Z.compress(v.astype(dv).tobytes());vd=np.frombuffer(D.decompress(vb),dv,count=v.size).astype(np.int32)
 else:dv=np.dtype('i1');vb=Z.compress(b'');vd=np.empty(0,np.int32)
 r=np.zeros(n,np.int32);r[mask]=vd;c.append((len(sb)+len(vb)+96,'sparse_'+dv.str,r))
 best=min(c,key=lambda x:x[0])
 if not np.array_equal(best[2],flat):raise RuntimeError(('int decode',best[1]))
 return best

def invrep(a,rep):
 if rep=='raw':return a
 if rep=='dt':return np.cumsum(a,axis=1,dtype=np.int32)
 if rep=='ds':return np.cumsum(a,axis=0,dtype=np.int32)
 if rep=='lorenzo':
  # inverse mixed first difference = cumulative sum over both axes
  return np.cumsum(np.cumsum(a,axis=0,dtype=np.int32),axis=1,dtype=np.int32)
 raise ValueError(rep)
def reps(q):
 q=np.asarray(q,np.int32);c=[]
 arr={'raw':q.copy()}
 dt=q.copy();dt[:,1:]-=q[:,:-1];arr['dt']=dt
 ds=q.copy();ds[1:]-=q[:-1];arr['ds']=ds
 L=q.copy();L[:,1:]-=q[:,:-1];L[1:,:]-=(q[:-1,:]-np.pad(q[:-1,:-1],((0,0),(1,0)))) # replaced below for clarity
 L=q.copy();L[1:,1:]=q[1:,1:]-q[:-1,1:]-q[1:,:-1]+q[:-1,:-1];L[0,1:]=q[0,1:]-q[0,:-1];L[1:,0]=q[1:,0]-q[:-1,0];arr['lorenzo']=L
 for name,a in arr.items():
  b,m,r=enc_int(a);qq=invrep(r.reshape(a.shape),name)
  if not np.array_equal(qq,q):raise RuntimeError(('rep decode',name))
  c.append((b+32,name+'_'+m,qq))
 return min(c,key=lambda x:x[0])

def frozen_checker(X,bound):
 nc,nt=X.shape;s=np.where(np.arange(nt)%2==0,1.0,-1.0);ZX=X*s[None,:];h=2*bound;phi=h/4.0
 cc=np.arange(nc)[:,None];tt=np.arange(nt)[None,:];mask=((cc+tt)&1)==0
 q=np.rint((ZX[mask]-phi)/h).astype(np.int32);cv=phi+h*q
 if float(np.max(np.abs(ZX[mask]-cv)))>bound*(1+1e-9):raise RuntimeError('control hard')
 P=np.zeros_like(ZX);P[mask]=cv
 ss=np.zeros_like(P);sc=np.zeros_like(P,dtype=np.int16);ts=np.zeros_like(P);tc=np.zeros_like(P,dtype=np.int16)
 ss[1:]+=P[:-1];sc[1:]+=1;ss[:-1]+=P[1:];sc[:-1]+=1
 ts[:,1:]+=P[:,:-1];tc[:,1:]+=1;ts[:,:-1]+=P[:,1:];tc[:,:-1]+=1
 miss=~mask;sp=np.divide(ss,sc,out=np.zeros_like(ss),where=sc>0);tp=np.divide(ts,tc,out=np.zeros_like(ts),where=tc>0)
 both=(sc>0)&(tc>0);P[miss&both]=(sp[miss&both]+tp[miss&both])/2;P[miss&(sc>0)&~both]=sp[miss&(sc>0)&~both];P[miss&(tc>0)&~both]=tp[miss&(tc>0)&~both]
 K=np.rint((ZX[miss]-P[miss])/h).astype(np.int32)
 A0=np.rint((ZX[0::2,0::2]-phi)/h).astype(np.int32);A1=np.rint((ZX[1::2,1::2]-phi)/h).astype(np.int32)
 f0=reps(A0);f1=reps(A1);fk=enc_int(K);A0d=f0[2];A1d=f1[2];Kd=fk[2]
 Pd=np.zeros_like(ZX);Pd[0::2,0::2]=phi+h*A0d;Pd[1::2,1::2]=phi+h*A1d
 ssum=np.zeros_like(Pd);sc=np.zeros_like(Pd,dtype=np.int16);tsum=np.zeros_like(Pd);tc=np.zeros_like(Pd,dtype=np.int16)
 ssum[1:]+=Pd[:-1];sc[1:]+=1;ssum[:-1]+=Pd[1:];sc[:-1]+=1;tsum[:,1:]+=Pd[:,:-1];tc[:,1:]+=1;tsum[:,:-1]+=Pd[:,1:];tc[:,:-1]+=1
 sp=np.divide(ssum,sc,out=np.zeros_like(ssum),where=sc>0);tp=np.divide(tsum,tc,out=np.zeros_like(tsum),where=tc>0);both=(sc>0)&(tc>0)
 Pd[miss&both]=(sp[miss&both]+tp[miss&both])/2;Pd[miss&(sc>0)&~both]=sp[miss&(sc>0)&~both];Pd[miss&(tc>0)&~both]=tp[miss&(tc>0)&~both];Pd[miss]+=h*Kd
 R=Pd*s[None,:];me=float(np.max(np.abs(X-R)))
 if not np.all(np.isfinite(R)) or not math.isfinite(me) or me>(bound/SAFETY)*(1+5e-6):raise RuntimeError(('ours hard',me,bound/SAFETY))
 total=f0[0]+f1[0]+fk[0]+96
 return {'bytes':total,'control_bytes':f0[0]+f1[0],'correction_bytes':fk[0]+96,'control_reps':[f0[1],f1[1]],'correction_rep':fk[1],'correction_nonzero':float(np.mean(K!=0)),'maxerr':me}

def main(path,slot):
 slot=int(slot)
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,std=stats(d);eps=.1*std;bound=eps*SAFETY
  if tuple(d.shape)!=(30000,6912):raise RuntimeError(('shape',d.shape))
  tblocks=list(range(slot*10,min(30,(slot+1)*10)));rows=[]
  for tb in tblocks:
   t0=tb*TB;t1=min(d.shape[0],t0+TB)
   for cb,c0 in enumerate(range(0,d.shape[1],CB)):
    c1=min(d.shape[1],c0+CB);X=np.asarray(d[t0:t1,c0:c1],np.float64).T;ours=frozen_checker(X,bound);sb,ori=szrun(X,eps);raw=X.size*2
    rows.append({'tb':tb,'cb':cb,'t0':t0,'t1':t1,'c0':c0,'c1':c1,'raw':raw,'ours':ours['bytes'],'sz3':sb,'gain':sb/ours['bytes'],'ours_bps':8*ours['bytes']/X.size,'sz3_bps':8*sb/X.size,'control_bytes':ours['control_bytes'],'correction_bytes':ours['correction_bytes'],'correction_nonzero':ours['correction_nonzero'],'sz3_orientation':ori,'maxerr':ours['maxerr']})
  raw=sum(r['raw'] for r in rows);ob=sum(r['ours'] for r in rows);sb=sum(r['sz3'] for r in rows)
  out={'slot':slot,'global_std':std,'eps':eps,'tiles':len(rows),'raw_bytes':raw,'ours_bytes':ob,'sz3_bytes':sb,'gain_vs_sz3':sb/ob,'ours_ratio':raw/ob,'sz3_ratio':raw/sb,'ours_bps':16*ob/raw,'sz3_bps':16*sb/raw,'min_tile_gain':min(r['gain'] for r in rows),'median_tile_gain':float(np.median([r['gain'] for r in rows])),'max_tile_gain':max(r['gain'] for r in rows),'control_bytes':sum(r['control_bytes'] for r in rows),'correction_bytes':sum(r['correction_bytes'] for r in rows),'rows':rows,'scope':'Frozen PR236 checkerboard definition on every 128x1024 tile in this one-third time partition: Nyquist demod true, temporal weight 1, phase 1, global 10%-std hard error. Control/correction arrays are actually compressed, byte-decoded and reconstruction verified. Matched SZ3 gets identical tile partition and best orientation, zero global metadata.'}
  print(json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2),flush=True);json.dump(out,open(f'imperial_frozen_checker_full_{slot}.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1],sys.argv[2])
