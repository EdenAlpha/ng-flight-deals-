#!/usr/bin/env python3
import os,subprocess,json,tempfile
import numpy as np
import video_probe as V
W,H,FPS=V.W,V.H,V.FPS

def motion_block(prev,cur,y0,x0,bs=16,rad=16):
    y1=min(cur.shape[0],y0+bs);x1=min(cur.shape[1],x0+bs);cb=cur[y0:y1,x0:x1]
    pad=np.pad(prev,rad,mode='edge');best=(10**30,0,0)
    # coarse four-pixel lattice, then exact refinement around its minimum
    for dy in range(-rad,rad+1,4):
      for dx in range(-rad,rad+1,4):
        pb=pad[y0+rad+dy:y1+rad+dy,x0+rad+dx:x1+rad+dx]
        sc=np.abs(cb[::2,::2].astype(np.int16)-pb[::2,::2].astype(np.int16)).sum()
        if sc<best[0]:best=(int(sc),dx,dy)
    _,bx,by=best;best=(10**30,bx,by)
    for dy in range(max(-rad,by-3),min(rad,by+3)+1):
      for dx in range(max(-rad,bx-3),min(rad,bx+3)+1):
        pb=pad[y0+rad+dy:y1+rad+dy,x0+rad+dx:x1+rad+dx]
        sc=np.abs(cb.astype(np.int16)-pb.astype(np.int16)).sum()
        if sc<best[0]:best=(int(sc),dx,dy)
    return best[1],best[2]

def spatial(cur):
    left=np.zeros_like(cur);left[:,1:]=cur[:,:-1];up=np.zeros_like(cur);up[1:]=cur[:-1];ul=np.zeros_like(cur);ul[1:,1:]=cur[:-1,:-1]
    return V.paeth(left,up,ul)
def temporal_x(cur,prev):
    left=np.zeros_like(cur);left[:,1:]=cur[:,:-1];pl=np.zeros_like(prev);pl[:,1:]=prev[:,:-1]
    return ((prev.astype(np.int16)+left.astype(np.int16)-pl.astype(np.int16))&255).astype(np.uint8)
def temporal_y(cur,prev):
    up=np.zeros_like(cur);up[1:]=cur[:-1];pu=np.zeros_like(prev);pu[1:]=prev[:-1]
    return ((prev.astype(np.int16)+up.astype(np.int16)-pu.astype(np.int16))&255).astype(np.uint8)

def encode_y(frames,bs=16):
    nf,h,w=frames.shape;res=np.empty_like(frames);modes=[];dxs=[];dys=[]
    for t in range(nf):
      cur=frames[t];sp=spatial(cur);prev=frames[t-1] if t else None
      tx=temporal_x(cur,prev) if t else None;ty=temporal_y(cur,prev) if t else None
      pad=np.pad(prev,16,mode='edge') if t else None
      for y0 in range(0,h,bs):
       for x0 in range(0,w,bs):
        y1=min(h,y0+bs);x1=min(w,x0+bs);cb=cur[y0:y1,x0:x1]
        candidates=[sp[y0:y1,x0:x1]]
        mv=(0,0)
        if t:
          dx,dy=motion_block(prev,cur,y0,x0,bs,16);mv=(dx,dy)
          mb=pad[y0+16+dy:y1+16+dy,x0+16+dx:x1+16+dx]
          candidates += [prev[y0:y1,x0:x1],tx[y0:y1,x0:x1],ty[y0:y1,x0:x1],mb]
        rr=[V.zz_from_mod(((cb.astype(np.int16)-p.astype(np.int16))&255).astype(np.uint8)) for p in candidates]
        scores=[V.entropy(q) for q in rr];k=int(np.argmin(scores));modes.append(k);dxs.append(mv[0]+16);dys.append(mv[1]+16);res[t,y0:y1,x0:x1]=rr[k]
      print('frame',t,'/',nf,flush=True)
    return res,bytes(modes),bytes(dxs),bytes(dys)

def decode_y(res,modes,dxs,dys,bs=16):
    nf,h,w=res.shape;out=np.empty_like(res);mi=0
    for t in range(nf):
      fr=np.zeros((h,w),dtype=np.uint8);prev=out[t-1] if t else None;pad=np.pad(prev,16,mode='edge') if t else None
      for y0 in range(0,h,bs):
       for x0 in range(0,w,bs):
        y1=min(h,y0+bs);x1=min(w,x0+bs);k=modes[mi];dx=dxs[mi]-16;dy=dys[mi]-16;mi+=1
        for y in range(y0,y1):
         for x in range(x0,x1):
          left=int(fr[y,x-1]) if x else 0;up=int(fr[y-1,x]) if y else 0;ul=int(fr[y-1,x-1]) if x and y else 0
          pp=left+up-ul;pa=abs(pp-left);pb=abs(pp-up);pc=abs(pp-ul);sp=left if pa<=pb and pa<=pc else up if pb<=pc else ul
          if k==0:pred=sp
          elif k==1:pred=int(prev[y,x])
          elif k==2:
            pl=int(prev[y,x-1]) if x else 0;pred=(int(prev[y,x])+left-pl)&255
          elif k==3:
            pu=int(prev[y-1,x]) if y else 0;pred=(int(prev[y,x])+up-pu)&255
          elif k==4:pred=int(pad[y+16+dy,x+16+dx])
          else:raise ValueError(k)
          z=int(res[t,y,x]);e=z//2 if z%2==0 else -((z+1)//2);fr[y,x]=(pred+e)&255
      out[t]=fr
    return out

def main():
    if not os.path.exists('media'):V.run(['git','clone','-q','--depth','1','https://github.com/chthomos/video-media-samples.git','media'])
    V.run(['ffmpeg','-loglevel','error','-y','-ss','0','-t','4','-i','media/big-buck-bunny-480p-30sec.mp4','-vf',f'scale={W}:{H}','-r',str(FPS),'-f','rawvideo','-pix_fmt','yuv420p','video.raw'])
    raw=open('video.raw','rb').read();Y,U,Ch=V.split(raw);nf=len(Y)
    yr,ym,xd,yd=encode_y(Y)
    ydec=decode_y(yr,ym,xd,yd)
    motions=[(0,0)]
    for t in range(1,nf):motions.append(V.find_shift(Y[t-1],Y[t]))
    ur,um=V.encode_plane(U,8,motions,2);vr,vm=V.encode_plane(Ch,8,motions,2)
    udec=V.decode_plane(ur,um,8,motions,2);vdec=V.decode_plane(vr,vm,8,motions,2)
    exact=V.join((ydec,udec,vdec))==raw
    streams=[yr.tobytes(),ym,xd,yd,ur.tobytes(),um,vr.tobytes(),vm,bytes((x+16)&31 for x,y in motions),bytes((y+16)&31 for x,y in motions)]
    ss=[V.best(s) for s in streams];total=64+sum(x[1] for x in ss)
    rawbest=V.best(raw);ff='ffv1.mkv';V.run(['ffmpeg','-loglevel','error','-y','-f','rawvideo','-pix_fmt','yuv420p','-s',f'{W}x{H}','-r',str(FPS),'-i','video.raw','-c:v','ffv1','-level','3','-coder','1','-context','1',ff]);ffs=os.path.getsize(ff)
    out={'original':len(raw),'frames':nf,'direct_best':rawbest[1],'ffv1':ffs,'axiom_local_motion':total,'vs_direct_pct':round((rawbest[1]-total)*100/rawbest[1],2),'vs_ffv1_pct':round((ffs-total)*100/ffs,2),'exact':exact,'streams':[{'codec':x[0],'size':x[1]} for x in ss]}
    open('video_block_results.json','w').write(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
