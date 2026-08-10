#!/usr/bin/env python3
import os,subprocess,tempfile,json,lzma,math
import numpy as np

W,H,FPS=320,180,24
RAW='video.raw'

def run(a,**kw): return subprocess.run(a,check=True,**kw)
def zz_from_mod(x):
    s=np.where(x<128,x.astype(np.int16),x.astype(np.int16)-256)
    return np.where(s>=0,2*s,-2*s-1).astype(np.uint8)
def unzz(z):
    z=z.astype(np.int16);s=np.where((z&1)==0,z//2,-((z+1)//2));return (s&255).astype(np.uint8)
def entropy(a):
    h=np.bincount(a.ravel(),minlength=256).astype(np.float64);h=h[h>0];p=h/h.sum();return float(-(p*np.log2(p)).sum())
def shift(a,dx,dy):
    h,w=a.shape;xs=np.clip(np.arange(w)-dx,0,w-1);ys=np.clip(np.arange(h)-dy,0,h-1);return a[np.ix_(ys,xs)]
def find_shift(prev,cur,rad=8):
    a=prev[::4,::4].astype(np.int16);b=cur[::4,::4].astype(np.int16);best=(10**30,0,0)
    for dy in range(-rad,rad+1):
      for dx in range(-rad,rad+1):
        sx=int(round(dx/4));sy=int(round(dy/4))
        x0=max(0,sx);x1=min(a.shape[1],a.shape[1]+sx);y0=max(0,sy);y1=min(a.shape[0],a.shape[0]+sy)
        qx=max(0,-sx);qy=max(0,-sy)
        if x1-x0<8 or y1-y0<8:continue
        sc=np.abs(b[y0:y1,x0:x1]-a[qy:qy+y1-y0,qx:qx+x1-x0]).sum()
        if sc<best[0]:best=(int(sc),dx,dy)
    return best[1],best[2]
def paeth(a,b,c):
    p=a.astype(np.int16)+b.astype(np.int16)-c.astype(np.int16);pa=np.abs(p-a);pb=np.abs(p-b);pc=np.abs(p-c);return np.where((pa<=pb)&(pa<=pc),a,np.where(pb<=pc,b,c)).astype(np.uint8)
def preds(cur,prev,mprev):
    left=np.zeros_like(cur);left[:,1:]=cur[:,:-1]
    up=np.zeros_like(cur);up[1:]=cur[:-1]
    ul=np.zeros_like(cur);ul[1:,1:]=cur[:-1,:-1]
    ps=[paeth(left,up,ul)]
    if prev is not None:
      ps.append(prev)
      pleft=np.zeros_like(prev);pleft[:,1:]=prev[:,:-1]
      pup=np.zeros_like(prev);pup[1:]=prev[:-1]
      ps.append(((prev.astype(np.int16)+left.astype(np.int16)-pleft.astype(np.int16))&255).astype(np.uint8))
      ps.append(((prev.astype(np.int16)+up.astype(np.int16)-pup.astype(np.int16))&255).astype(np.uint8))
      ps.append(mprev)
    return ps
def encode_plane(frames,block=16,motions=None,scale=1):
    nf,h,w=frames.shape;res=np.empty_like(frames);modes=[]
    for t in range(nf):
      cur=frames[t];prev=frames[t-1] if t else None
      mp=None
      if t:
        dx,dy=motions[t];dx=int(round(dx/scale));dy=int(round(dy/scale));mp=shift(prev,dx,dy)
      pp=preds(cur,prev,mp)
      rr=[zz_from_mod(((cur.astype(np.int16)-p.astype(np.int16))&255).astype(np.uint8)) for p in pp]
      for y in range(0,h,block):
       for x in range(0,w,block):
        y1=min(h,y+block);x1=min(w,x+block)
        scores=[entropy(q[y:y1,x:x1]) for q in rr]
        k=int(np.argmin(scores));modes.append(k);res[t,y:y1,x:x1]=rr[k][y:y1,x:x1]
    return res,bytes(modes)
def decode_plane(res,modes,block=16,motions=None,scale=1):
    nf,h,w=res.shape;out=np.empty_like(res);mi=0
    for t in range(nf):
      fr=np.zeros((h,w),dtype=np.uint8);prev=out[t-1] if t else None
      dx=dy=0
      if t: dx=int(round(motions[t][0]/scale));dy=int(round(motions[t][1]/scale));mp=shift(prev,dx,dy)
      else: mp=None
      for y0 in range(0,h,block):
       for x0 in range(0,w,block):
        y1=min(h,y0+block);x1=min(w,x0+block);k=modes[mi];mi+=1
        # raster decode because spatial predictors are causal
        for y in range(y0,y1):
         for x in range(x0,x1):
          left=int(fr[y,x-1]) if x else 0;up=int(fr[y-1,x]) if y else 0;ul=int(fr[y-1,x-1]) if x and y else 0
          p=left+up-ul;pa=abs(p-left);pb=abs(p-up);pc=abs(p-ul);sp=left if pa<=pb and pa<=pc else up if pb<=pc else ul
          if k==0:pred=sp
          elif k==1:pred=int(prev[y,x])
          elif k==2:
            pl=int(prev[y,x-1]) if x else 0;pred=(int(prev[y,x])+left-pl)&255
          elif k==3:
            pu=int(prev[y-1,x]) if y else 0;pred=(int(prev[y,x])+up-pu)&255
          elif k==4:pred=int(mp[y,x])
          else:raise ValueError(k)
          z=int(res[t,y,x]);e=z//2 if z%2==0 else -((z+1)//2);fr[y,x]=(pred+e)&255
      out[t]=fr
    return out
def split(raw):
    fs=W*H*3//2;nf=len(raw)//fs;a=np.frombuffer(raw,dtype=np.uint8);Y=[];U=[];V=[];p=0
    for _ in range(nf):
      Y.append(a[p:p+W*H].reshape(H,W));p+=W*H
      U.append(a[p:p+W*H//4].reshape(H//2,W//2));p+=W*H//4
      V.append(a[p:p+W*H//4].reshape(H//2,W//2));p+=W*H//4
    return np.stack(Y),np.stack(U),np.stack(V)
def join(ps):
    Y,U,V=ps;o=bytearray()
    for t in range(len(Y)):o+=Y[t].tobytes()+U[t].tobytes()+V[t].tobytes()
    return bytes(o)
def csize(data,codec):
    if codec=='xz':return len(lzma.compress(data,preset=9|lzma.PRESET_EXTREME))
    f=tempfile.NamedTemporaryFile(delete=False);f.write(data);f.close();out=f.name+'.out'
    try:
      if codec=='br':cmd=['brotli','-q','11','-c',f.name]
      else:cmd=['zstd','-22','--ultra','-q','-f',f.name,'-o',out]
      if codec=='br':
       with open(out,'wb') as g:run(cmd,stdout=g)
      else:run(cmd)
      return os.path.getsize(out)
    finally:
      for q in (f.name,out):
       try:os.remove(q)
       except:pass
def best(data):
    v={c:csize(data,c) for c in ('xz','br','zstd')};k=min(v,key=v.get);return k,v[k],v
def main():
    run(['git','clone','-q','--depth','1','https://github.com/chthomos/video-media-samples.git','media'])
    run(['ffmpeg','-loglevel','error','-y','-ss','0','-t','4','-i','media/big-buck-bunny-480p-30sec.mp4','-vf',f'scale={W}:{H}','-r',str(FPS),'-f','rawvideo','-pix_fmt','yuv420p',RAW])
    raw=open(RAW,'rb').read();Y,U,V=split(raw);nf=len(Y)
    motions=[(0,0)]
    for t in range(1,nf):motions.append(find_shift(Y[t-1],Y[t]))
    enc=[];maps=[]
    for A,b,s in ((Y,16,1),(U,8,2),(V,8,2)):
      r,m=encode_plane(A,b,motions,s);enc.append(r);maps.append(m)
    dec=[]
    for r,m,b,s in ((enc[0],maps[0],16,1),(enc[1],maps[1],8,2),(enc[2],maps[2],8,2)):
      dec.append(decode_plane(r,m,b,motions,s))
    exact=join(dec)==raw
    raw_best=best(raw)
    streams=[x.tobytes() for x in enc]+maps+[bytes((dx+16)&31 for dx,dy in motions),bytes((dy+16)&31 for dx,dy in motions)]
    sv=[];total=64
    for i,s in enumerate(streams):
      q=best(s);sv.append(q);total+=q[1]
    # specialist FFV1
    ff='ffv1.mkv';run(['ffmpeg','-loglevel','error','-y','-f','rawvideo','-pix_fmt','yuv420p','-s',f'{W}x{H}','-r',str(FPS),'-i',RAW,'-c:v','ffv1','-level','3','-coder','1','-context','1',ff]);ffs=os.path.getsize(ff)
    out={'original':len(raw),'frames':nf,'direct_best':{'codec':raw_best[0],'size':raw_best[1],'all':raw_best[2]},'ffv1':ffs,'axiom_3d_block_law':total,'axiom_vs_direct_pct':round((raw_best[1]-total)*100/raw_best[1],2),'axiom_vs_ffv1_pct':round((ffs-total)*100/ffs,2),'exact':exact,'motions':motions[:12],'streams':[{'codec':q[0],'size':q[1]} for q in sv]}
    open('video_results.json','w').write(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
