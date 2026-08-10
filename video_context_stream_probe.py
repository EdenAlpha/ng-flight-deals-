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
def split_streams(res,modes,meta,keyextra=None):
 gs={}
 for m in meta:
  i,t,y,x,y1,x1=m;mode=modes[i];extra=keyextra(m) if keyextra and mode==4 else ();key=(mode,)+tuple(extra);gs.setdefault(key,[]).append(m)
 out={}
 for k in sorted(gs):
  q=bytearray()
  for _,t,y,x,y1,x1 in gs[k]:q+=res[t,y:y1,x:x1].tobytes()
  out[k]=bytes(q)
 return out,gs
def unsplit_streams(streams,groups,shape):
 out=np.empty(shape,dtype=np.uint8)
 for k in sorted(groups):
  q=streams[k];p=0
  for _,t,y,x,y1,x1 in groups[k]:
   n=(y1-y)*(x1-x);out[t,y:y1,x:x1]=np.frombuffer(q[p:p+n],dtype=np.uint8).reshape(y1-y,x1-x);p+=n
  if p!=len(q):raise ValueError('trailing')
 return out
def bestcost(b):
 direct=V.best(b);best={'method':'direct','size':direct[1],'parts':[{'codec':direct[0],'size':direct[1]}]}
 a=np.frombuffer(b,dtype=np.uint8)
 if len(a):
  mask=np.packbits((a!=0).astype(np.uint8),bitorder='little').tobytes();nz=a[a!=0].tobytes();mm=V.best(mask);nn=V.best(nz) if nz else ('none',0,{}) ;s=mm[1]+nn[1]+3
  if s<best['size']:best={'method':'sparse','size':s,'parts':[{'codec':mm[0],'size':mm[1]},{'codec':nn[0],'size':nn[1]}]}
  bp=[];s=10
  for bit in range(8):
   x=np.packbits(((a>>bit)&1).astype(np.uint8),bitorder='little').tobytes();z=V.best(x);bp.append({'codec':z[0],'size':z[1]});s+=z[1]
  if s<best['size']:best={'method':'bitplanes','size':s,'parts':bp}
 return best
def main():
 if not os.path.exists('media'):V.run(['git','clone','-q','--depth','1','https://github.com/chthomos/video-media-samples.git','media'])
 V.run(['ffmpeg','-loglevel','error','-y','-ss','0','-t','4','-i','media/big-buck-bunny-480p-30sec.mp4','-vf',f'scale={W}:{H}','-r',str(FPS),'-f','rawvideo','-pix_fmt','yuv420p','video.raw'])
 raw=open('video.raw','rb').read();Y,U,C=V.split(raw);nf=len(Y);yr,ym,xd,yd=B.encode_y(Y);motions=[(0,0)]+[V.find_shift(Y[t-1],Y[t]) for t in range(1,nf)];ur,um=V.encode_plane(U,8,motions,2);vr,vm=V.encode_plane(C,8,motions,2);my=metas(nf,H,W,16);mc=metas(nf,H//2,W//2,8)
 ys,yg=split_streams(yr,ym,my,lambda m:(xd[m[0]],yd[m[0]]));us,ug=split_streams(ur,um,mc,lambda m:(int(round(motions[m[1]][0]/2)),int(round(motions[m[1]][1]/2))));vs,vg=split_streams(vr,vm,mc,lambda m:(int(round(motions[m[1]][0]/2)),int(round(motions[m[1]][1]/2))))
 yri=unsplit_streams(ys,yg,yr.shape);uri=unsplit_streams(us,ug,ur.shape);vri=unsplit_streams(vs,vg,vr.shape);exact=np.array_equal(yri,yr) and np.array_equal(uri,ur) and np.array_equal(vri,vr) and V.join((B.decode_y(yri,ym,xd,yd),V.decode_plane(uri,um,8,motions,2),V.decode_plane(vri,vm,8,motions,2)))==raw
 details=[];rescost=0
 for pn,ss in [('Y',ys),('U',us),('V',vs)]:
  for k,b in ss.items():
   c=bestcost(b);rescost+=c['size'];details.append({'plane':pn,'key':list(k),'raw':len(b),**c});print(details[-1],flush=True)
 maps=[V.best(q) for q in (ym,xd,yd,um,vm,bytes((x+16)&31 for x,y in motions),bytes((y+16)&31 for x,y in motions))];mapcost=sum(x[1] for x in maps);over=256+12*len(details);total=rescost+mapcost+over
 out={'original':len(raw),'x265_lossless':778751,'previous_axiom':881279,'residual_cost':rescost,'map_cost':mapcost,'overhead_estimate':over,'total':total,'vs_x265_pct':round((778751-total)*100/778751,2),'exact':bool(exact),'stream_count':len(details),'details':details};open('video_context_stream_results.json','w').write(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='details'},indent=2))
if __name__=='__main__':main()
