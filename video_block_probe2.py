#!/usr/bin/env python3
import os,json
import numpy as np
import video_probe as V
import video_block_probe as B
W,H,FPS=V.W,V.H,V.FPS

def spatial(cur):
 l=np.zeros_like(cur);l[:,1:]=cur[:,:-1];u=np.zeros_like(cur);u[1:]=cur[:-1];ul=np.zeros_like(cur);ul[1:,1:]=cur[:-1,:-1];return V.paeth(l,u,ul)
def tx(cur,prev):
 l=np.zeros_like(cur);l[:,1:]=cur[:,:-1];pl=np.zeros_like(prev);pl[:,1:]=prev[:,:-1];return ((prev.astype(np.int16)+l.astype(np.int16)-pl.astype(np.int16))&255).astype(np.uint8)
def ty(cur,prev):
 u=np.zeros_like(cur);u[1:]=cur[:-1];pu=np.zeros_like(prev);pu[1:]=prev[:-1];return ((prev.astype(np.int16)+u.astype(np.int16)-pu.astype(np.int16))&255).astype(np.uint8)

def encode_chroma(frames,ydx,ydy,bs=8):
 nf,h,w=frames.shape;res=np.empty_like(frames);modes=[];mi=0
 for t in range(nf):
  cur=frames[t];sp=spatial(cur);prev=frames[t-1] if t else None;xx=tx(cur,prev) if t else None;yy=ty(cur,prev) if t else None;pad=np.pad(prev,8,mode='edge') if t else None
  for y0 in range(0,h,bs):
   for x0 in range(0,w,bs):
    y1=min(h,y0+bs);x1=min(w,x0+bs);cb=cur[y0:y1,x0:x1];dx=int(round((ydx[mi]-16)/2));dy=int(round((ydy[mi]-16)/2));c=[sp[y0:y1,x0:x1]]
    if t:
      mb=pad[y0+8+dy:y1+8+dy,x0+8+dx:x1+8+dx];c += [prev[y0:y1,x0:x1],xx[y0:y1,x0:x1],yy[y0:y1,x0:x1],mb]
    rr=[V.zz_from_mod(((cb.astype(np.int16)-p.astype(np.int16))&255).astype(np.uint8)) for p in c];scores=[V.entropy(q) for q in rr];k=int(np.argmin(scores));modes.append(k);res[t,y0:y1,x0:x1]=rr[k];mi+=1
 return res,bytes(modes)

def decode_chroma(res,modes,ydx,ydy,bs=8):
 nf,h,w=res.shape;out=np.empty_like(res);mi=0
 for t in range(nf):
  fr=np.zeros((h,w),dtype=np.uint8);prev=out[t-1] if t else None;pad=np.pad(prev,8,mode='edge') if t else None
  for y0 in range(0,h,bs):
   for x0 in range(0,w,bs):
    y1=min(h,y0+bs);x1=min(w,x0+bs);k=modes[mi];dx=int(round((ydx[mi]-16)/2));dy=int(round((ydy[mi]-16)/2));mi+=1
    for y in range(y0,y1):
     for x in range(x0,x1):
      left=int(fr[y,x-1]) if x else 0;up=int(fr[y-1,x]) if y else 0;ul=int(fr[y-1,x-1]) if x and y else 0;pp=left+up-ul;pa=abs(pp-left);pb=abs(pp-up);pc=abs(pp-ul);sp=left if pa<=pb and pa<=pc else up if pb<=pc else ul
      if k==0:pred=sp
      elif k==1:pred=int(prev[y,x])
      elif k==2:
       pl=int(prev[y,x-1]) if x else 0;pred=(int(prev[y,x])+left-pl)&255
      elif k==3:
       pu=int(prev[y-1,x]) if y else 0;pred=(int(prev[y,x])+up-pu)&255
      elif k==4:pred=int(pad[y+8+dy,x+8+dx])
      else:raise ValueError(k)
      z=int(res[t,y,x]);e=z//2 if z%2==0 else -((z+1)//2);fr[y,x]=(pred+e)&255
  out[t]=fr
 return out

def main():
 if not os.path.exists('media'):V.run(['git','clone','-q','--depth','1','https://github.com/chthomos/video-media-samples.git','media'])
 V.run(['ffmpeg','-loglevel','error','-y','-ss','0','-t','4','-i','media/big-buck-bunny-480p-30sec.mp4','-vf',f'scale={W}:{H}','-r',str(FPS),'-f','rawvideo','-pix_fmt','yuv420p','video.raw'])
 raw=open('video.raw','rb').read();Y,U,C=V.split(raw);yr,ym,xd,yd=B.encode_y(Y);ydec=B.decode_y(yr,ym,xd,yd);ur,um=encode_chroma(U,xd,yd);vr,vm=encode_chroma(C,xd,yd);ud=decode_chroma(ur,um,xd,yd);vd=decode_chroma(vr,vm,xd,yd);exact=V.join((ydec,ud,vd))==raw
 streams=[yr.tobytes(),ym,xd,yd,ur.tobytes(),um,vr.tobytes(),vm];ss=[V.best(s) for s in streams];total=64+sum(x[1] for x in ss);rb=V.best(raw);ff='ffv1.mkv';V.run(['ffmpeg','-loglevel','error','-y','-f','rawvideo','-pix_fmt','yuv420p','-s',f'{W}x{H}','-r',str(FPS),'-i','video.raw','-c:v','ffv1','-level','3','-coder','1','-context','1',ff]);ffs=os.path.getsize(ff)
 out={'original':len(raw),'ffv1':ffs,'direct_best':rb[1],'axiom_shared_motion':total,'vs_ffv1_pct':round((ffs-total)*100/ffs,2),'vs_direct_pct':round((rb[1]-total)*100/rb[1],2),'exact':exact,'streams':[{'codec':x[0],'size':x[1]} for x in ss]};open('video_block2_results.json','w').write(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
