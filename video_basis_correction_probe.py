#!/usr/bin/env python3
import os,subprocess,json,tempfile
import numpy as np
W,H,FPS=320,180,24

def run(a,check=True,**kw):return subprocess.run(a,check=check,**kw)
def brotli_size(data):
 f=tempfile.NamedTemporaryFile(delete=False);f.write(data);f.close();o=f.name+'.br'
 try:
  with open(o,'wb') as g:run(['brotli','-q','11','-c',f.name],stdout=g)
  return os.path.getsize(o)
 finally:
  for p in (f.name,o):
   try:os.remove(p)
   except:pass
def zigzag_mod(orig,base):
 m=((orig.astype(np.int16)-base.astype(np.int16))&255).astype(np.uint8);s=np.where(m<128,m.astype(np.int16),m.astype(np.int16)-256);return np.where(s>=0,2*s,-2*s-1).astype(np.uint8)
def inv(base,z):
 s=np.where((z&1)==0,z.astype(np.int16)//2,-((z.astype(np.int16)+1)//2));return ((base.astype(np.int16)+s)&255).astype(np.uint8)
def bitplane_sizes(z):
 rows=[];total=0
 for bit in range(8):
  q=np.packbits(((z>>bit)&1).astype(np.uint8),bitorder='little').tobytes();s=brotli_size(q);rows.append({'bit':bit,'ones':int(((z>>bit)&1).sum()),'compressed':s});total+=s
 return total,rows
def main():
 if not os.path.exists('media'):run(['git','clone','-q','--depth','1','https://github.com/chthomos/video-media-samples.git','media'])
 run(['ffmpeg','-loglevel','error','-y','-ss','0','-t','4','-i','media/big-buck-bunny-480p-30sec.mp4','-vf',f'scale={W}:{H}','-r',str(FPS),'-f','rawvideo','-pix_fmt','yuv420p','video.raw'])
 ob=open('video.raw','rb').read();orig=np.frombuffer(ob,dtype=np.uint8).copy();rows=[]
 for crf in (10,14,18,22,26,30):
  enc=f'basis_{crf}.mkv';dec=f'basis_{crf}.raw';print('CRF',crf,flush=True)
  run(['ffmpeg','-loglevel','error','-y','-f','rawvideo','-pix_fmt','yuv420p','-s',f'{W}x{H}','-r',str(FPS),'-i','video.raw','-c:v','libx265','-preset','slow','-crf',str(crf),'-x265-params','log-level=error','-pix_fmt','yuv420p',enc])
  run(['ffmpeg','-loglevel','error','-y','-i',enc,'-f','rawvideo','-pix_fmt','yuv420p',dec]);bb=open(dec,'rb').read();base=np.frombuffer(bb,dtype=np.uint8).copy()
  if len(base)!=len(orig):rows.append({'crf':crf,'error':'length'});continue
  z=zigzag_mod(orig,base);exact=np.array_equal(inv(base,z),orig);byte=brotli_size(z.tobytes());bp,bpr=bitplane_sizes(z);basis=os.path.getsize(enc);bestcorr=min(byte,bp);method='bytes' if byte<=bp else 'bitplanes';total=basis+bestcorr+128
  r={'crf':crf,'basis':basis,'residual_bytes_br':byte,'bitplanes_br':bp,'correction':bestcorr,'method':method,'total':total,'exact':bool(exact),'vs_lossless_x265_pct':round((778751-total)*100/778751,2),'bitplanes':bpr};rows.append(r);print({k:v for k,v in r.items() if k!='bitplanes'},flush=True)
 best=min((r for r in rows if r.get('exact')),key=lambda r:r['total']);out={'original':len(orig),'lossless_x265':778751,'rows':rows,'best':best};open('video_basis_correction_results.json','w').write(json.dumps(out,indent=2));print(json.dumps({'best':best},indent=2))
if __name__=='__main__':main()
