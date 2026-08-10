#!/usr/bin/env python3
import os,json
import numpy as np
import video_probe as V
import video_block_probe as B
W,H,FPS=V.W,V.H,V.FPS

def zz_scalar(m):
 s=m if m<128 else m-256;return 2*s if s>=0 else -2*s-1
def unzz_scalar(z):return (z//2 if z%2==0 else -((z+1)//2))&255
def metas(nf,h,w,bs):
 o=[];i=0
 for t in range(nf):
  for y in range(0,h,bs):
   for x in range(0,w,bs):o.append((i,t,y,x,min(h,y+bs),min(w,x+bs)));i+=1
 return o
def groups(meta,modes,bs):
 g={}
 for m in meta:
  i,t,y,x,y1,x1=m;g.setdefault((modes[i],y//bs,x//bs),[]).append(m)
 return g
def encode(res,g,kind):
 o=bytearray()
 for k in sorted(g):
  gs=sorted(g[k],key=lambda m:m[1]);hh=gs[0][4]-gs[0][2];ww=gs[0][5]-gs[0][3]
  if kind=='blocks':
   for _,t,y,x,y1,x1 in gs:o+=res[t,y:y1,x:x1].tobytes()
  else:
   for iy in range(hh):
    for ix in range(ww):
     vals=[int(res[t,y+iy,x+ix]) for _,t,y,x,y1,x1 in gs]
     if kind=='lanes':o+=bytes(vals)
     else:
      if vals:
       o.append(vals[0]);prev=vals[0]
       for v in vals[1:]:o.append(zz_scalar((v-prev)&255));prev=v
 return bytes(o)
def decode(blob,shape,g,kind):
 out=np.empty(shape,dtype=np.uint8);p=0
 for k in sorted(g):
  gs=sorted(g[k],key=lambda m:m[1]);hh=gs[0][4]-gs[0][2];ww=gs[0][5]-gs[0][3]
  if kind=='blocks':
   for _,t,y,x,y1,x1 in gs:
    n=(y1-y)*(x1-x);out[t,y:y1,x:x1]=np.frombuffer(blob[p:p+n],dtype=np.uint8).reshape(y1-y,x1-x);p+=n
  else:
   for iy in range(hh):
    for ix in range(ww):
     if kind=='lanes':vals=list(blob[p:p+len(gs)]);p+=len(gs)
     else:
      vals=[]
      if gs:
       prev=blob[p];p+=1;vals.append(prev)
       for _ in range(1,len(gs)):
        e=unzz_scalar(blob[p]);p+=1;prev=(prev+(e if e<128 else e-256))&255;vals.append(prev)
     for m,v in zip(gs,vals):_,t,y,x,y1,x1=m;out[t,y+iy,x+ix]=v
 if p!=len(blob):raise ValueError('trailing')
 return out
def main():
 if not os.path.exists('media'):V.run(['git','clone','-q','--depth','1','https://github.com/chthomos/video-media-samples.git','media'])
 V.run(['ffmpeg','-loglevel','error','-y','-ss','0','-t','4','-i','media/big-buck-bunny-480p-30sec.mp4','-vf',f'scale={W}:{H}','-r',str(FPS),'-f','rawvideo','-pix_fmt','yuv420p','video.raw'])
 raw=open('video.raw','rb').read();Y,U,C=V.split(raw);nf=len(Y);yr,ym,xd,yd=B.encode_y(Y);motions=[(0,0)]+[V.find_shift(Y[t-1],Y[t]) for t in range(1,nf)];ur,um=V.encode_plane(U,8,motions,2);vr,vm=V.encode_plane(C,8,motions,2);my=metas(nf,H,W,16);mc=metas(nf,H//2,W//2,8);gy=groups(my,ym,16);gu=groups(mc,um,8);gv=groups(mc,vm,8)
 maps=[V.best(q) for q in (ym,xd,yd,um,vm,bytes((x+16)&31 for x,y in motions),bytes((y+16)&31 for x,y in motions))];mapcost=sum(x[1] for x in maps);rows=[]
 for kind in ('blocks','lanes','lane_delta'):
  ss=[encode(yr,gy,kind),encode(ur,gu,kind),encode(vr,gv,kind)];inv=[decode(ss[0],yr.shape,gy,kind),decode(ss[1],ur.shape,gu,kind),decode(ss[2],vr.shape,gv,kind)];exact=np.array_equal(inv[0],yr) and np.array_equal(inv[1],ur) and np.array_equal(inv[2],vr) and V.join((B.decode_y(inv[0],ym,xd,yd),V.decode_plane(inv[1],um,8,motions,2),V.decode_plane(inv[2],vm,8,motions,2)))==raw
  cs=[V.best(q) for q in ss];total=64+mapcost+sum(x[1] for x in cs);r={'kind':kind,'total':total,'exact':bool(exact),'residuals':[{'codec':x[0],'size':x[1]} for x in cs]};rows.append(r);print(r,flush=True)
 best=min((r for r in rows if r['exact']),key=lambda r:r['total']);out={'original':len(raw),'x265_lossless':778751,'lawcoord_previous':841774,'best':best,'vs_x265_pct':round((778751-best['total'])*100/778751,2),'rows':rows};open('video_trajectory_results.json','w').write(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
