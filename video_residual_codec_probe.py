#!/usr/bin/env python3
import os,json,subprocess,tempfile
import video_probe as V
import video_block_probe as B
W,H,FPS=V.W,V.H,V.FPS

def run(a,check=True,**kw): return subprocess.run(a,check=check,**kw)
def cbytes(data,kind):
 f=tempfile.NamedTemporaryFile(delete=False);f.write(data);f.close();o=f.name+'.o'
 try:
  if kind=='br':
   with open(o,'wb') as g:run(['brotli','-q','11','-c',f.name],stdout=g)
  elif kind=='xz':run(['xz','-9e','-k','-f',f.name]);os.rename(f.name+'.xz',o)
  else:run(['zstd','-22','--ultra','-q','-f',f.name,'-o',o])
  return os.path.getsize(o)
 finally:
  for p in (f.name,o):
   try:os.remove(p)
   except:pass
def bestmap(data):return min((cbytes(data,k),k) for k in ('br','xz','zstd'))
def encode_video(raw,out,codec):
 if codec=='x265': args=['-c:v','libx265','-preset','veryslow','-x265-params','lossless=1:log-level=error','-pix_fmt','yuv420p']
 elif codec=='x264': args=['-c:v','libx264','-preset','veryslow','-qp','0','-pix_fmt','yuv420p']
 else: raise ValueError(codec)
 run(['ffmpeg','-loglevel','error','-y','-f','rawvideo','-pix_fmt','yuv420p','-s',f'{W}x{H}','-r',str(FPS),'-i',raw]+args+[out])
def decode_video(inp,out):run(['ffmpeg','-loglevel','error','-y','-i',inp,'-f','rawvideo','-pix_fmt','yuv420p',out])
def main():
 if not os.path.exists('media'):run(['git','clone','-q','--depth','1','https://github.com/chthomos/video-media-samples.git','media'])
 run(['ffmpeg','-loglevel','error','-y','-ss','0','-t','4','-i','media/big-buck-bunny-480p-30sec.mp4','-vf',f'scale={W}:{H}','-r',str(FPS),'-f','rawvideo','-pix_fmt','yuv420p','video.raw'])
 raw=open('video.raw','rb').read();Y,U,C=V.split(raw);nf=len(Y)
 yr,ym,xd,yd=B.encode_y(Y)
 motions=[(0,0)]+[V.find_shift(Y[t-1],Y[t]) for t in range(1,nf)]
 ur,um=V.encode_plane(U,8,motions,2);vr,vm=V.encode_plane(C,8,motions,2)
 residual=V.join((yr,ur,vr));open('residual.yuv','wb').write(residual)
 # verify transform before coding
 y0=B.decode_y(yr,ym,xd,yd);u0=V.decode_plane(ur,um,8,motions,2);v0=V.decode_plane(vr,vm,8,motions,2);transform_exact=V.join((y0,u0,v0))==raw
 maps=[ym,xd,yd,um,vm,bytes((dx+16)&31 for dx,dy in motions),bytes((dy+16)&31 for dx,dy in motions)]
 maprows=[bestmap(m) for m in maps];maps_total=sum(x[0] for x in maprows)
 rows=[]
 for codec in ('x265','x264'):
  enc=codec+'.mkv';dec=codec+'.yuv';encode_video('residual.yuv',enc,codec);decode_video(enc,dec);residual_exact=open(dec,'rb').read()==residual
  total=os.path.getsize(enc)+maps_total+64
  rows.append({'codec':codec,'residual_video':os.path.getsize(enc),'maps':maps_total,'total':total,'residual_exact':residual_exact,'original_exact':transform_exact and residual_exact,'vs_raw_x265_pct':round((778751-total)*100/778751,2)})
 out={'original':len(raw),'raw_x265_lossless':778751,'raw_x264_lossless':787605,'rows':rows,'maps':[{'size':s,'codec':c} for s,c in maprows]};open('video_residual_codec_results.json','w').write(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
