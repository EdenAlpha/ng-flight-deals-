#!/usr/bin/env python3
import os,subprocess,tempfile,shutil,time,json,sys
ROOT=os.path.dirname(os.path.abspath(__file__));OUT=os.path.join(ROOT,'out');os.makedirs(OUT,exist_ok=True);sys.path.insert(0,ROOT)
import video_law_v6 as v6
RAW='/tmp/sintel.yuv';MP4='/tmp/sintel.mp4';W=320;H=180;FPS=24
subprocess.run(['curl','-L','--retry','3','-sS','https://media.w3.org/2010/05/sintel/trailer.mp4','-o',MP4],check=True)
subprocess.run(['ffmpeg','-loglevel','error','-y','-ss','0','-t','4','-i',MP4,'-vf',f'scale={W}:{H}','-r',str(FPS),'-f','rawvideo','-pix_fmt','yuv420p',RAW],check=True)
D=open(RAW,'rb').read();t=time.time();R=v6.pack(D,W,H,16);pack_s=time.time()-t;t=time.time();dec=v6.unpack(R);unpack_s=time.time()-t;exact=dec==D
if not exact:raise SystemExit('AXIOM VIDEO ROUNDTRIP FAILED')
def general(blob):
 td=tempfile.mkdtemp();f=os.path.join(td,'x');open(f,'wb').write(blob);o={}
 subprocess.run(['xz','-9e','-k','-f',f],check=True);o['xz9e']=os.path.getsize(f+'.xz')
 subprocess.run(['brotli','-q','11','-f',f,'-o',f+'.br'],check=True);o['brotli11']=os.path.getsize(f+'.br')
 subprocess.run(['zstd','-22','--ultra','-q','-f',f,'-o',f+'.zst'],check=True);o['zstd22']=os.path.getsize(f+'.zst');shutil.rmtree(td);return o
def codec(name,args):
 out=f'/tmp/{name}.mkv';back=f'/tmp/{name}.yuv'
 try:
  subprocess.run(['ffmpeg','-loglevel','error','-y','-f','rawvideo','-pix_fmt','yuv420p','-s:v',f'{W}x{H}','-r',str(FPS),'-i',RAW]+args+[out],check=True,timeout=600)
  subprocess.run(['ffmpeg','-loglevel','error','-y','-i',out,'-f','rawvideo','-pix_fmt','yuv420p',back],check=True,timeout=300)
  if open(back,'rb').read()!=D:return None
  return os.path.getsize(out)
 except Exception:return None
rawg=general(D); axg=general(R);spec={}
for name,args in [
 ('ffv1_ctx0',['-c:v','ffv1','-level','3','-coder','1','-context','0','-g','1']),
 ('ffv1_ctx1',['-c:v','ffv1','-level','3','-coder','1','-context','1','-g','1']),
 ('x264_lossless',['-c:v','libx264','-preset','veryslow','-qp','0']),
 ('x265_lossless',['-c:v','libx265','-preset','slower','-x265-params','lossless=1:log-level=error'])]:
 s=codec(name,args)
 if s is not None:spec[name]=s
opponents=dict(rawg);opponents.update(spec);best_name=min(opponents,key=opponents.get);best=opponents[best_name];ab=min(axg.values());res={'category':'raw_video_v6','original':len(D),'representation':len(R),'axiom_backends':axg,'axiom_best':ab,'opponents':opponents,'opponent_best_name':best_name,'opponent_best':best,'win_pct':round((best-ab)*100/best,2),'exact':exact,'pack_s':round(pack_s,2),'unpack_s':round(unpack_s,2)}
print('RESULT',json.dumps(res),flush=True);open(os.path.join(OUT,'beast_results.json'),'w').write(json.dumps(res,indent=2))
