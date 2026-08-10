#!/usr/bin/env python3
import os,subprocess,json
import video_probe as V
import video_context_v2_probe as X

# X.main() asks V.run() to decode the Big Buck Bunny clip into video.raw.
# Replace only that corpus-generation call with the reproducible FFmpeg testsrc2 law.
os.makedirs('media',exist_ok=True)
_orig=V.run
def _run(args,**kw):
    if args and args[0]=='ffmpeg' and any('big-buck-bunny' in str(a) for a in args):
        return subprocess.run([
            'ffmpeg','-loglevel','error','-y','-f','lavfi',
            '-i','testsrc2=size=320x180:rate=24','-t','4',
            '-pix_fmt','yuv420p','-f','rawvideo','video.raw'
        ],check=True)
    return _orig(args,**kw)
V.run=_run
X.main()
r=json.load(open('video_context_v2_results.json'))
r['corpus']='ffmpeg testsrc2 320x180 24fps 4s yuv420p'
r['specialist_ffv1_exact']=418062
r['vs_ffv1_pct']=round((418062-r['total'])*100/418062,2)
open('video_context_hard_results.json','w').write(json.dumps(r,indent=2))
print(json.dumps({k:v for k,v in r.items() if k not in ('details','maps')},indent=2))
