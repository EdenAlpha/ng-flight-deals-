#!/usr/bin/env python3
import os,subprocess,time,json,numpy as np
OUT='beast/out';os.makedirs(OUT,exist_ok=True);RAW='/tmp/sintel.yuv';MP4='/tmp/sintel.mp4';W=320;H=180;FPS=24
subprocess.run(['curl','-L','--retry','3','-sS','https://media.w3.org/2010/05/sintel/trailer.mp4','-o',MP4],check=True)
subprocess.run(['ffmpeg','-loglevel','error','-y','-ss','0','-t','4','-i',MP4,'-vf',f'scale={W}:{H}','-r',str(FPS),'-f','rawvideo','-pix_fmt','yuv420p',RAW],check=True)
D=open(RAW,'rb').read();FS=W*H*3//2;T=len(D)//FS

def split(raw):
 a=np.frombuffer(raw,dtype=np.uint8);p=0;Y=[];U=[];V=[]
 for _ in range(T):Y.append(a[p:p+W*H].reshape(H,W));p+=W*H;U.append(a[p:p+W*H//4].reshape(H//2,W//2));p+=W*H//4;V.append(a[p:p+W*H//4].reshape(H//2,W//2));p+=W*H//4
 return [np.stack(Y),np.stack(U),np.stack(V)]
def join(P):
 o=bytearray()
 for t in range(T):o+=P[0][t].tobytes()+P[1][t].tobytes()+P[2][t].tobytes()
 return bytes(o)
def zmap(r):
 r=((r.astype(np.int16)+128)&255)-128
 return np.where(r>=0,2*r,-2*r-1).astype(np.uint8)
def unz(z):
 z=z.astype(np.int16);return np.where((z&1)==0,z//2,-((z+1)//2)).astype(np.int16)

def encode_plane(a,law):
 q=a.astype(np.int16)
 if law=='t1':
  p=np.zeros_like(q);p[1:]=q[:-1];r=q-p
 elif law=='t2':
  p=np.zeros_like(q);p[1:]=2*q[:-1];p[2:]-=q[:-2];r=q-p
 elif law in ('dx','tx'):
  dx=np.empty_like(q);dx[:,:,0]=q[:,:,0];dx[:,:,1:]=q[:,:,1:]-q[:,:,:-1]
  if law=='dx':r=dx
  else:
   p=np.zeros_like(dx);p[1:]=dx[:-1];r=dx-p
 elif law in ('dy','ty'):
  dy=np.empty_like(q);dy[:,0]=q[:,0];dy[:,1:]=q[:,1:]-q[:,:-1]
  if law=='dy':r=dy
  else:
   p=np.zeros_like(dy);p[1:]=dy[:-1];r=dy-p
 else:raise ValueError(law)
 return zmap(r)
def decode_plane(z,law):
 r=unz(z);T0,H0,W0=r.shape;o=np.empty_like(z)
 if law=='t1':
  prev=np.zeros((H0,W0),dtype=np.int16)
  for t in range(T0):cur=(prev+r[t])&255;o[t]=cur;prev=cur
 elif law=='t2':
  p1=np.zeros((H0,W0),dtype=np.int16);p2=np.zeros((H0,W0),dtype=np.int16)
  for t in range(T0):cur=(2*p1-p2+r[t])&255;o[t]=cur;p2,p1=p1,cur
 elif law in ('dx','tx'):
  prevdx=np.zeros((H0,W0),dtype=np.int16)
  for t in range(T0):
   dx=((prevdx+r[t])&255) if law=='tx' else (r[t]&255);cur=np.cumsum(dx,axis=1)&255;o[t]=cur.astype(np.uint8);prevdx=dx
 elif law in ('dy','ty'):
  prevdy=np.zeros((H0,W0),dtype=np.int16)
  for t in range(T0):
   dy=((prevdy+r[t])&255) if law=='ty' else (r[t]&255);cur=np.cumsum(dy,axis=0)&255;o[t]=cur.astype(np.uint8);prevdy=dy
 return o
P=split(D)
def transform(law):return join([encode_plane(x,law) for x in P])
def invert(raw,law):return join([decode_plane(x,law) for x in split(raw)])

def ffv1(inp,name,ctx=0):
 src=f'/tmp/{name}.yuv';out=f'/tmp/{name}.mkv';back=f'/tmp/{name}.back';open(src,'wb').write(inp)
 subprocess.run(['ffmpeg','-loglevel','error','-y','-f','rawvideo','-pix_fmt','yuv420p','-s:v',f'{W}x{H}','-r',str(FPS),'-i',src,'-c:v','ffv1','-level','3','-coder','1','-context',str(ctx),'-g','1',out],check=True)
 subprocess.run(['ffmpeg','-loglevel','error','-y','-i',out,'-f','rawvideo','-pix_fmt','yuv420p',back],check=True)
 q=open(back,'rb').read()
 if q!=inp:raise SystemExit('ffv1 not exact '+name)
 return os.path.getsize(out),q,out
base0,_,_=ffv1(D,'orig0',0);base1,_,_=ffv1(D,'orig1',1);base=min(base0,base1)
rows=[]
for law in ['t1','t2','dx','dy','tx','ty']:
 t=time.time();R=transform(law);assert invert(R,law)==D
 for ctx in (0,1):
  size,back,_=ffv1(R,f'{law}_{ctx}',ctx);exact=invert(back,law)==D;rows.append({'law':law,'ctx':ctx,'bytes':size+16,'exact':exact,'transform_s':round(time.time()-t,2)});print('CAND',rows[-1],flush=True)
best=min(rows,key=lambda x:x['bytes']);res={'category':'video_v7_ffv1_basis','original':len(D),'ffv1_original':{'ctx0':base0,'ctx1':base1,'best':base},'candidates':rows,'axiom_best':best,'win_pct':round((base-best['bytes'])*100/base,2)}
print('RESULT',json.dumps(res),flush=True);open(os.path.join(OUT,'beast_results.json'),'w').write(json.dumps(res,indent=2))
