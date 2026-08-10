#!/usr/bin/env python3
import os,subprocess,json,shutil
import text_transform_probe as T

def run(a,**kw):return subprocess.run(a,check=True,**kw)
def ppmd(name,data):
 fn=name+'.bin';arc=name+'.7z';open(fn,'wb').write(data);run(['7z','a','-bd','-y','-t7z','-m0=PPMd','-mx=9',arc,fn],stdout=subprocess.DEVNULL);return os.path.getsize(arc)
def main():
 run(['curl','-L','-sS','https://www.gutenberg.org/files/1342/1342-0.txt','-o','prose.txt']);raw=open('prose.txt','rb').read();rep=T.pack_words(raw);exact=T.unpack_words(rep)==raw
 rawp=ppmd('raw',raw);repp=ppmd('rep',rep);out={'original':len(raw),'representation':len(rep),'raw_ppmd':rawp,'axiom_word_ppmd':repp,'exact':exact,'improvement_pct':round((rawp-repp)*100/rawp,2)};open('text_ppmd_results.json','w').write(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
