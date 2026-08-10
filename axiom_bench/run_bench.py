#!/usr/bin/env python3
import os,subprocess,csv,hashlib,shutil,sys,time
ROOT=os.path.dirname(os.path.abspath(__file__))
OUT=os.path.join(ROOT,'out'); os.makedirs(OUT,exist_ok=True)

def run(cmd,**kw):
 return subprocess.run(cmd,check=True,**kw)
def size(p): return os.path.getsize(p)
def sh(cmd): run(['bash','-lc',cmd])

def prepare():
 os.makedirs(os.path.join(ROOT,'data'),exist_ok=True); d=os.path.join(ROOT,'data')
 # Real prose
 sh(f"curl -L --retry 3 -sS https://www.gutenberg.org/files/1342/1342-0.txt -o '{d}/prose.txt'")
 # Real structured JSON corpus
 sh(f"curl -L --retry 3 -sS https://raw.githubusercontent.com/json-iterator/test-data/master/large-file.json -o '{d}/data.json'")
 # Real large CSV; cap to first 250k rows for predictable runtime
 sh(f"curl -L --retry 3 -sS https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-counties.csv | head -n 250001 > '{d}/data.csv'")
 # Real source tree
 sh(f"rm -rf '{d}/zlib-src'; git clone -q --depth 1 https://github.com/madler/zlib.git '{d}/zlib-src'; rm -rf '{d}/zlib-src/.git'; tar --sort=name --mtime='UTC 2020-01-01' --owner=0 --group=0 -cf '{d}/source_tree.tar' -C '{d}/zlib-src' .")
 # Real Android application source tree, before APK packaging
 sh(f"rm -rf '{d}/android-src'; git clone -q --depth 1 https://github.com/android/architecture-samples.git '{d}/android-src'; rm -rf '{d}/android-src/.git'; tar --sort=name --mtime='UTC 2020-01-01' --owner=0 --group=0 -cf '{d}/android_app_raw.tar' -C '{d}/android-src' app build.gradle.kts settings.gradle.kts gradle.properties 2>/dev/null || tar --sort=name --mtime='UTC 2020-01-01' --owner=0 --group=0 -cf '{d}/android_app_raw.tar' -C '{d}/android-src' app")
 # Real image decoded to raw RGB pixels
 sh(f"curl -L --retry 3 -sS https://raw.githubusercontent.com/opencv/opencv/master/samples/data/lena.jpg -o '{d}/lena.jpg'; ffmpeg -loglevel error -y -i '{d}/lena.jpg' -f rawvideo -pix_fmt rgb24 '{d}/image_rgb24.raw'")
 # Real video decoded to lossless raw YUV frames (short segment, downscaled only to keep benchmark bounded)
 sh(f"curl -L --retry 3 -sS https://media.w3.org/2010/05/sintel/trailer.mp4 -o '{d}/video.mp4'; ffmpeg -loglevel error -y -ss 0 -t 4 -i '{d}/video.mp4' -vf scale=320:180 -r 24 -f rawvideo -pix_fmt yuv420p '{d}/video_yuv420.raw'")
 # Real executable from runner
 shutil.copy2('/usr/bin/bash',f'{d}/bash.elf')
 # ZIP/DEFLATE control: real Python wheel
 sh(f"python3 -m pip download -q --no-deps pygments==2.19.1 -d '{d}/wheel'; cp '{d}'/wheel/*.whl '{d}/package.whl'")
 # Related-file collection: 30 consecutive revisions of one real source file from zlib history
 sh(f"rm -rf '{d}/zlib-history'; git clone -q https://github.com/madler/zlib.git '{d}/zlib-history'; mkdir -p '{d}/versions'; cd '{d}/zlib-history'; git log --format=%H -- zlib.h | head -n 30 | nl -w3 -nrz | while read n h; do git show $h:zlib.h > '{d}/versions'/zlib_$n.h || true; done; tar --sort=name --mtime='UTC 2020-01-01' --owner=0 --group=0 -cf '{d}/related_versions.tar' -C '{d}/versions' .; rm -rf '{d}/zlib-history'")

def bench(label,path):
 base=os.path.join(OUT,label); ax=base+'.axm'; dec=base+'.dec'; zst=base+'.zst'; xz=base+'.xz'; br=base+'.br'
 t=time.time(); cp=run([sys.executable,os.path.join(ROOT,'axiom2.py'),'c',path,ax],stdout=subprocess.PIPE,text=True); at=time.time()-t
 run([sys.executable,os.path.join(ROOT,'axiom2.py'),'d',ax,dec],stdout=subprocess.PIPE,text=True)
 exact=hashlib.sha256(open(path,'rb').read()).digest()==hashlib.sha256(open(dec,'rb').read()).digest()
 run(['zstd','-22','--ultra','-q','-f',path,'-o',zst])
 run(['xz','-9e','-k','-f',path]); shutil.move(path+'.xz',xz)
 with open(br,'wb') as f: run(['brotli','-q','11','-c',path],stdout=f)
 vals={'zstd22':size(zst),'xz9e':size(xz),'brotli11':size(br)}; best_name=min(vals,key=vals.get); best=vals[best_name]
 mode='unknown'
 s=cp.stdout.strip();
 if "'mode':" in s:
  mode=s.split("'mode':",1)[1].split(',',1)[0].strip().strip("'{} ")
 return {'category':label,'original':size(path),'axiom':size(ax),**vals,'best_baseline':best,'best_name':best_name,'axiom_vs_best_pct':round((best-size(ax))*100/best,2),'orig_reduction_pct':round((size(path)-size(ax))*100/size(path),2),'mode':mode,'exact_roundtrip':exact,'axiom_seconds':round(at,2)}

def main():
 prepare(); d=os.path.join(ROOT,'data')
 tests=[
 ('plain_txt',f'{d}/prose.txt'),('json',f'{d}/data.json'),('csv',f'{d}/data.csv'),('source_tree',f'{d}/source_tree.tar'),('raw_android_app',f'{d}/android_app_raw.tar'),('raw_image_rgb24',f'{d}/image_rgb24.raw'),('raw_video_yuv420',f'{d}/video_yuv420.raw'),('executable_elf',f'{d}/bash.elf'),('zip_wheel_control',f'{d}/package.whl'),('related_file_versions',f'{d}/related_versions.tar')]
 rows=[]
 for label,p in tests:
  print('BENCH',label,size(p),flush=True); rows.append(bench(label,p)); print(rows[-1],flush=True)
 out=os.path.join(OUT,'results.csv')
 with open(out,'w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
 with open(os.path.join(OUT,'results.md'),'w') as f:
  f.write('|category|original|AXIOM|zstd22|xz9e|brotli11|best baseline|AXIOM vs best|mode|exact|\n|---|---:|---:|---:|---:|---:|---:|---:|---|---|\n')
  for r in rows:f.write(f"|{r['category']}|{r['original']}|{r['axiom']}|{r['zstd22']}|{r['xz9e']}|{r['brotli11']}|{r['best_baseline']} ({r['best_name']})|{r['axiom_vs_best_pct']}%|{r['mode']}|{r['exact_roundtrip']}|\n")
 print('\nFINAL_RESULTS');print(open(out).read())
if __name__=='__main__': main()
