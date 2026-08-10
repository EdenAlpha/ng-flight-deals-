#!/usr/bin/env python3
import os,subprocess,json,hashlib
W,H,FPS=320,180,24

def run(a,check=True,**kw): return subprocess.run(a,check=check,**kw)
def exact(file):
 out=file+'.raw';r=run(['ffmpeg','-loglevel','error','-y','-i',file,'-f','rawvideo','-pix_fmt','yuv420p',out],check=False)
 ok=r.returncode==0 and open(out,'rb').read()==open('video.raw','rb').read()
 try:os.remove(out)
 except:pass
 return ok

def enc(name,args):
 out=name+'.mkv';cmd=['ffmpeg','-loglevel','error','-y','-f','rawvideo','-pix_fmt','yuv420p','-s',f'{W}x{H}','-r',str(FPS),'-i','video.raw']+args+[out]
 r=run(cmd,check=False)
 if r.returncode:return {'name':name,'ok':False,'error':'encode failed'}
 return {'name':name,'ok':exact(out),'size':os.path.getsize(out)}

def main():
 if not os.path.exists('media'):run(['git','clone','-q','--depth','1','https://github.com/chthomos/video-media-samples.git','media'])
 run(['ffmpeg','-loglevel','error','-y','-ss','0','-t','4','-i','media/big-buck-bunny-480p-30sec.mp4','-vf',f'scale={W}:{H}','-r',str(FPS),'-f','rawvideo','-pix_fmt','yuv420p','video.raw'])
 cases=[
 ('ffv1_c1_ctx1',['-c:v','ffv1','-level','3','-coder','1','-context','1']),
 ('ffv1_c1_ctx0',['-c:v','ffv1','-level','3','-coder','1','-context','0']),
 ('ffv1_c0_ctx0',['-c:v','ffv1','-level','3','-coder','0','-context','0']),
 ('ffv1_c2_ctx1',['-c:v','ffv1','-level','3','-coder','2','-context','1']),
 ('ffv1_c1_ctx1_nocrc',['-c:v','ffv1','-level','3','-coder','1','-context','1','-slicecrc','0']),
 ('ffv1_c1_ctx0_nocrc',['-c:v','ffv1','-level','3','-coder','1','-context','0','-slicecrc','0']),
 ('x264_lossless',['-c:v','libx264','-preset','veryslow','-qp','0','-pix_fmt','yuv420p']),
 ('x265_lossless',['-c:v','libx265','-preset','veryslow','-x265-params','lossless=1:log-level=error','-pix_fmt','yuv420p']),
 ('huffyuv',['-c:v','huffyuv','-pix_fmt','yuv422p'])
 ]
 rows=[]
 for n,a in cases:
  print('RUN',n,flush=True);rows.append(enc(n,a));print(rows[-1],flush=True)
 valid=[x for x in rows if x.get('ok')]
 best=min(valid,key=lambda x:x['size']) if valid else None
 out={'original':os.path.getsize('video.raw'),'rows':rows,'best_exact':best,'axiom_local_motion':881279}
 if best:out['axiom_vs_best_pct']=round((best['size']-881279)*100/best['size'],2)
 open('video_baselines_results.json','w').write(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
