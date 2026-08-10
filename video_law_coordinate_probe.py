#!/usr/bin/env python3
import os,json
import numpy as np
import video_probe as V
import video_block_probe as B
W,H,FPS=V.W,V.H,V.FPS

def blocks(nf,h,w,bs):
 o=[];i=0
 for t in range(nf):
  for y in range(0,h,bs):
   for x in range(0,w,bs):
    o.append((i,t,y,x,min(h,y+bs),min(w,x+bs)));i+=1
 return o
def key_y(meta,modes,dx,dy,motion=False):
 i=meta[0];m=modes[i]
 return (m,dx[i],dy[i]) if motion and m==4 else (m,0,0)
def key_c(meta,modes,motions,scale=2,motion=False):
 i,t=meta[0],meta[1];m=modes[i]
 if motion and m==4:
  dx=int(round(motions[t][0]/scale));dy=int(round(motions[t][1]/scale));return (m,dx,dy)
 return (m,0,0)
def order_blocks(res,metas,keyfn,lane=False):
 groups={}
 for m in metas:groups.setdefault(keyfn(m),[]).append(m)
 out=bytearray()
 for k in sorted(groups):
  gs=groups[k]
  if not lane:
   for _,t,y,x,y1,x1 in gs:out+=res[t,y:y1,x:x1].tobytes()
  else:
   maxh=max(m[4]-m[2] for m in gs);maxw=max(m[5]-m[3] for m in gs)
   for iy in range(maxh):
    for ix in range(maxw):
     for _,t,y,x,y1,x1 in gs:
      if y+iy<y1 and x+ix<x1:out.append(int(res[t,y+iy,x+ix]))
 return bytes(out)
def unorder(blob,shape,metas,keyfn,lane=False):
 out=np.empty(shape,dtype=np.uint8);groups={};p=0
 for m in metas:groups.setdefault(keyfn(m),[]).append(m)
 for k in sorted(groups):
  gs=groups[k]
  if not lane:
   for _,t,y,x,y1,x1 in gs:
    n=(y1-y)*(x1-x);out[t,y:y1,x:x1]=np.frombuffer(blob[p:p+n],dtype=np.uint8).reshape(y1-y,x1-x);p+=n
  else:
   maxh=max(m[4]-m[2] for m in gs);maxw=max(m[5]-m[3] for m in gs)
   for iy in range(maxh):
    for ix in range(maxw):
     for _,t,y,x,y1,x1 in gs:
      if y+iy<y1 and x+ix<x1:out[t,y+iy,x+ix]=blob[p];p+=1
 if p!=len(blob):raise ValueError('trailing')
 return out
def main():
 if not os.path.exists('media'):V.run(['git','clone','-q','--depth','1','https://github.com/chthomos/video-media-samples.git','media'])
 V.run(['ffmpeg','-loglevel','error','-y','-ss','0','-t','4','-i','media/big-buck-bunny-480p-30sec.mp4','-vf',f'scale={W}:{H}','-r',str(FPS),'-f','rawvideo','-pix_fmt','yuv420p','video.raw'])
 raw=open('video.raw','rb').read();Y,U,C=V.split(raw);nf=len(Y);yr,ym,xd,yd=B.encode_y(Y);motions=[(0,0)]+[V.find_shift(Y[t-1],Y[t]) for t in range(1,nf)];ur,um=V.encode_plane(U,8,motions,2);vr,vm=V.encode_plane(C,8,motions,2)
 my=blocks(nf,H,W,16);mc=blocks(nf,H//2,W//2,8)
 candidates=[]
 for motion in (False,True):
  for lane in (False,True):
   ys=order_blocks(yr,my,lambda m:key_y(m,ym,xd,yd,motion),lane);us=order_blocks(ur,mc,lambda m:key_c(m,um,motions,2,motion),lane);vs=order_blocks(vr,mc,lambda m:key_c(m,vm,motions,2,motion),lane)
   # exact reorder inverse + original inverse
   yri=unorder(ys,yr.shape,my,lambda m:key_y(m,ym,xd,yd,motion),lane);uri=unorder(us,ur.shape,mc,lambda m:key_c(m,um,motions,2,motion),lane);vri=unorder(vs,vr.shape,mc,lambda m:key_c(m,vm,motions,2,motion),lane)
   exact=np.array_equal(yri,yr) and np.array_equal(uri,ur) and np.array_equal(vri,vr) and V.join((B.decode_y(yri,ym,xd,yd),V.decode_plane(uri,um,8,motions,2),V.decode_plane(vri,vm,8,motions,2)))==raw
   sz=[]
   for q in (ys,us,vs):sz.append(V.best(q))
   maps=[V.best(q) for q in (ym,xd,yd,um,vm,bytes((x+16)&31 for x,y in motions),bytes((y+16)&31 for x,y in motions))]
   total=64+sum(q[1] for q in sz)+sum(q[1] for q in maps);r={'motion_key':motion,'lane_transpose':lane,'total':total,'exact':bool(exact),'residuals':[{'codec':q[0],'size':q[1]} for q in sz]};candidates.append(r);print(r,flush=True)
 best=min((r for r in candidates if r['exact']),key=lambda r:r['total']);out={'original':len(raw),'x265_lossless':778751,'previous_axiom':881279,'best':best,'vs_x265_pct':round((778751-best['total'])*100/778751,2),'candidates':candidates};open('video_law_coordinate_results.json','w').write(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
