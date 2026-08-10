#!/usr/bin/env python3
import os,subprocess,json
import numpy as np
W=H=512

def run(a,check=True,**kw):return subprocess.run(a,check=check,**kw)
def zz(d):
 s=np.where(d<128,d.astype(np.int16),d.astype(np.int16)-256);return np.where(s>=0,2*s,-2*s-1).astype(np.uint8)
def unzz(z):
 z=z.astype(np.int16);s=np.where((z&1)==0,z//2,-((z+1)//2));return (s&255).astype(np.uint8)
def med_pred(a):
 l=np.zeros_like(a);l[:,1:]=a[:,:-1];u=np.zeros_like(a);u[1:]=a[:-1];ul=np.zeros_like(a);ul[1:,1:]=a[:-1,:-1]
 lo=np.minimum(l,u);hi=np.maximum(l,u);p=l.astype(np.int16)+u.astype(np.int16)-ul.astype(np.int16);return np.where(ul>=hi,lo,np.where(ul<=lo,hi,p)).astype(np.uint8)
def pack_color(a):
 r=a[:,:,0];g=a[:,:,1];b=a[:,:,2];return np.stack([g,zz(((r.astype(np.int16)-g.astype(np.int16))&255).astype(np.uint8)),zz(((b.astype(np.int16)-g.astype(np.int16))&255).astype(np.uint8))],2)
def unpack_color(q):
 g=q[:,:,0];dr=unzz(q[:,:,1]);db=unzz(q[:,:,2]);return np.stack([((g.astype(np.int16)+np.where(dr<128,dr.astype(np.int16),dr.astype(np.int16)-256))&255).astype(np.uint8),g,((g.astype(np.int16)+np.where(db<128,db.astype(np.int16),db.astype(np.int16)-256))&255).astype(np.uint8)],2)
def spatial(a):
 out=np.empty_like(a)
 for c in range(3):
  p=med_pred(a[:,:,c]);out[:,:,c]=zz(((a[:,:,c].astype(np.int16)-p.astype(np.int16))&255).astype(np.uint8))
 return out
def unspatial(q):
 out=np.zeros_like(q)
 for c in range(3):
  for y in range(H):
   for x in range(W):
    l=int(out[y,x-1,c]) if x else 0;u=int(out[y-1,x,c]) if y else 0;ul=int(out[y-1,x-1,c]) if x and y else 0;lo=min(l,u);hi=max(l,u);p=lo if ul>=hi else hi if ul<=lo else l+u-ul;z=int(q[y,x,c]);e=z//2 if z%2==0 else -((z+1)//2);out[y,x,c]=(p+e)&255
 return out
def ppm(path,a):open(path,'wb').write(f'P6\n{W} {H}\n255\n'.encode()+a.tobytes())
def readppm(path):
 b=open(path,'rb').read();p=0;parts=[]
 while len(parts)<4:
  while p<len(b) and chr(b[p]).isspace():p+=1
  q=p
  while q<len(b) and not chr(b[q]).isspace():q+=1
  parts.append(b[p:q]);p=q
 while p<len(b) and chr(b[p]).isspace():p+=1
 return np.frombuffer(b[p:],dtype=np.uint8).reshape(H,W,3).copy()
def jxl(name,a):
 inp=name+'.ppm';enc=name+'.jxl';dec=name+'.dec.ppm';ppm(inp,a);run(['cjxl',inp,enc,'-d','0','-e','9','--quiet']);run(['djxl',enc,dec,'--quiet']);q=readppm(dec);return os.path.getsize(enc),np.array_equal(q,a)
def main():
 run(['curl','-L','-sS','https://raw.githubusercontent.com/opencv/opencv/master/samples/data/lena.jpg','-o','lena.jpg']);run(['ffmpeg','-loglevel','error','-y','-i','lena.jpg','-f','rawvideo','-pix_fmt','rgb24','rgb.raw']);a=np.frombuffer(open('rgb.raw','rb').read(),dtype=np.uint8).reshape(H,W,3).copy()
 variants={'raw':a,'color':pack_color(a),'spatial':spatial(a),'color_spatial':spatial(pack_color(a))};rows=[]
 for n,q in variants.items():
  s,codec_exact=jxl(n,q)
  if n=='raw': orig=q
  elif n=='color':orig=unpack_color(q)
  elif n=='spatial':orig=unspatial(q)
  else:orig=unpack_color(unspatial(q))
  exact=codec_exact and np.array_equal(orig,a);rows.append({'variant':n,'jxl_size':s,'exact':bool(exact)});print(rows[-1],flush=True)
 base=next(x['jxl_size'] for x in rows if x['variant']=='raw');best=min((x for x in rows if x['exact']),key=lambda x:x['jxl_size']);out={'original':a.size,'raw_jxl':base,'best':best,'improvement_pct':round((base-best['jxl_size'])*100/base,2),'rows':rows};open('image_jxl_prefilter_results.json','w').write(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
