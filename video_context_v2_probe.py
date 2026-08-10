#!/usr/bin/env python3
import os,json
import numpy as np
import video_probe as V
import video_block_probe as B
W,H,FPS=V.W,V.H,V.FPS

def metas(nf,h,w,bs):
 o=[];i=0
 for t in range(nf):
  for y in range(0,h,bs):
   for x in range(0,w,bs):o.append((i,t,y,x,min(h,y+bs),min(w,x+bs)));i+=1
 return o
def split_mode(res,modes,meta):
 gs={}
 for m in meta:gs.setdefault(modes[m[0]],[]).append(m)
 out={}
 for k in sorted(gs):
  q=bytearray()
  for _,t,y,x,y1,x1 in gs[k]:q+=res[t,y:y1,x:x1].tobytes()
  out[k]=bytes(q)
 return out,gs
def unsplit(streams,groups,shape):
 out=np.empty(shape,dtype=np.uint8)
 for k in sorted(groups):
  q=streams[k];p=0
  for _,t,y,x,y1,x1 in groups[k]:
   n=(y1-y)*(x1-x);out[t,y:y1,x:x1]=np.frombuffer(q[p:p+n],dtype=np.uint8).reshape(y1-y,x1-x);p+=n
  if p!=len(q):raise ValueError('trailing')
 return out
def c(q):return V.best(q)
def pack_nibbles(a):
 n=len(a);z=np.zeros((n+1)//2,dtype=np.uint8)
 z[:n//2]=(a[0:2*(n//2):2]&15)|((a[1:2*(n//2):2]&15)<<4)
 if n&1:z[-1]=a[-1]&15
 return z.tobytes()
def bestcost(b):
 a=np.frombuffer(b,dtype=np.uint8);d=c(b);best={'method':'direct','size':d[1],'parts':[{'codec':d[0],'size':d[1]}]}
 if not len(a):return best
 mask=np.packbits((a!=0).astype(np.uint8),bitorder='little').tobytes();nz=a[a!=0];mm=c(mask);nn=c(nz.tobytes()) if len(nz) else ('none',0,{})
 s=mm[1]+nn[1]+3
 if s<best['size']:best={'method':'sparse','size':s,'parts':[{'codec':mm[0],'size':mm[1]},{'codec':nn[0],'size':nn[1]}]}
 # sparse + nibble-coordinate magnitudes
 if len(nz):
  hi=(nz>>4).astype(np.uint8);lo=(nz&15).astype(np.uint8);hp=pack_nibbles(hi);lp=pack_nibbles(lo);hc=c(hp);lc=c(lp);s=mm[1]+hc[1]+lc[1]+5
  if s<best['size']:best={'method':'sparse_nibbles','size':s,'parts':[{'codec':mm[0],'size':mm[1]},{'codec':hc[0],'size':hc[1]},{'codec':lc[0],'size':lc[1]}]}
 # full bitplane coordinate
 parts=[];s=10
 for bit in range(8):
  q=np.packbits(((a>>bit)&1).astype(np.uint8),bitorder='little').tobytes();z=c(q);parts.append({'codec':z[0],'size':z[1]});s+=z[1]
 if s<best['size']:best={'method':'bitplanes','size':s,'parts':parts}
 return best
def map_best(mode_bytes,nf,bpf):
 a=np.frombuffer(mode_bytes,dtype=np.uint8).reshape(nf,bpf);raw=c(mode_bytes);tr=c(a.T.tobytes());return min((raw[1],'frame',raw),(tr[1],'trajectory',tr),key=lambda x:x[0])
def main():
 if not os.path.exists('media'):V.run(['git','clone','-q','--depth','1','https://github.com/chthomos/video-media-samples.git','media'])
 V.run(['ffmpeg','-loglevel','error','-y','-ss','0','-t','4','-i','media/big-buck-bunny-480p-30sec.mp4','-vf',f'scale={W}:{H}','-r',str(FPS),'-f','rawvideo','-pix_fmt','yuv420p','video.raw'])
 raw=open('video.raw','rb').read();Y,U,Cc=V.split(raw);nf=len(Y);yr,ym,xd,yd=B.encode_y(Y);motions=[(0,0)]+[V.find_shift(Y[t-1],Y[t]) for t in range(1,nf)];ur,um=V.encode_plane(U,8,motions,2);vr,vm=V.encode_plane(Cc,8,motions,2);my=metas(nf,H,W,16);mc=metas(nf,H//2,W//2,8)
 ys,yg=split_mode(yr,ym,my);us,ug=split_mode(ur,um,mc);vs,vg=split_mode(vr,vm,mc);yri=unsplit(ys,yg,yr.shape);uri=unsplit(us,ug,ur.shape);vri=unsplit(vs,vg,vr.shape)
 # Store local motion coordinates ONLY for blocks whose decoded mode consumes them.
 mx=bytes(xd[i] for i,m in enumerate(ym) if m==4);myv=bytes(yd[i] for i,m in enumerate(ym) if m==4);x2=bytearray([16])*len(ym);y2=bytearray([16])*len(ym);p=0
 for i,m in enumerate(ym):
  if m==4:x2[i]=mx[p];y2[i]=myv[p];p+=1
 exact=np.array_equal(yri,yr) and np.array_equal(uri,ur) and np.array_equal(vri,vr) and bytes(x2[i] for i,m in enumerate(ym) if m==4)==mx and V.join((B.decode_y(yri,ym,bytes(x2),bytes(y2)),V.decode_plane(uri,um,8,motions,2),V.decode_plane(vri,vm,8,motions,2)))==raw
 details=[];rescost=0
 for pn,ss in [('Y',ys),('U',us),('V',vs)]:
  for k,b in ss.items():q=bestcost(b);rescost+=q['size'];details.append({'plane':pn,'mode':int(k),'raw':len(b),**q});print(details[-1],flush=True)
 bpfy=((W+15)//16)*((H+15)//16);bpfc=((W//2+7)//8)*((H//2+7)//8);mode_results=[];mapcost=0
 for name,b,bpf in [('ym',ym,bpfy),('um',um,bpfc),('vm',vm,bpfc)]:
  q=map_best(b,nf,bpf);mapcost+=q[0];mode_results.append({'name':name,'layout':q[1],'size':q[0],'codec':q[2][0]})
 for name,b in [('mx_used',mx),('my_used',myv),('gdx',bytes((x+16)&31 for x,y in motions)),('gdy',bytes((y+16)&31 for x,y in motions))]:
  q=c(b);mapcost+=q[1];mode_results.append({'name':name,'layout':'used-only','size':q[1],'codec':q[0],'raw':len(b)})
 over=192+10*len(details);total=rescost+mapcost+over;out={'original':len(raw),'x265_lossless':778751,'context_v1':791807,'residual_cost':rescost,'map_cost':mapcost,'overhead_estimate':over,'total':total,'vs_x265_pct':round((778751-total)*100/778751,2),'exact':bool(exact),'details':details,'maps':mode_results};open('video_context_v2_results.json','w').write(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k not in ('details','maps')},indent=2));print(mode_results)
if __name__=='__main__':main()
