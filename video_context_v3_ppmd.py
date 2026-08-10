#!/usr/bin/env python3
import os,tempfile,subprocess
import video_probe as V
import video_context_v2_probe as X

def ppmd_size(data):
    if not data:return 0
    td=tempfile.mkdtemp();src=os.path.join(td,'s');arc=os.path.join(td,'s.7z')
    try:
        open(src,'wb').write(data)
        subprocess.run(['7z','a','-bd','-y','-t7z','-m0=PPMd','-mx=9',arc,src],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        return os.path.getsize(arc)
    finally:
        import shutil;shutil.rmtree(td,ignore_errors=True)

def stronger(data):
    old=V.best(data)
    try:p=ppmd_size(data)
    except Exception:return old
    return ('ppmd',p,{}) if p<old[1] else old

X.c=stronger
X.main()
# rename output so artifact is unambiguous
os.rename('video_context_v2_results.json','video_context_v3_results.json')
