#!/usr/bin/env python3
import os,subprocess,tempfile,shutil,time,json,sys
ROOT=os.path.dirname(os.path.abspath(__file__));OUT=os.path.join(ROOT,'out');os.makedirs(OUT,exist_ok=True);sys.path.insert(0,ROOT)
import csv_graph_transform_v5 as csv5
rawcsv='/tmp/all.csv';data='/tmp/data.csv'
subprocess.run(['curl','-L','--retry','3','-sS','https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-counties.csv','-o',rawcsv],check=True)
subprocess.run(['bash','-lc',f'head -n 250001 {rawcsv} > {data}'],check=True)
D=open(data,'rb').read();t=time.time();R=csv5.pack(D);pack_s=time.time()-t;exact=csv5.unpack(R)==D
if not exact:raise SystemExit('roundtrip failed')
def sizes(blob):
    td=tempfile.mkdtemp();f=os.path.join(td,'x');open(f,'wb').write(blob);o={}
    subprocess.run(['xz','-9e','-k','-f',f],check=True);o['xz9e']=os.path.getsize(f+'.xz')
    subprocess.run(['brotli','-q','11','-f',f,'-o',f+'.br'],check=True);o['brotli11']=os.path.getsize(f+'.br')
    subprocess.run(['zstd','-22','--ultra','-q','-f',f,'-o',f+'.zst'],check=True);o['zstd22']=os.path.getsize(f+'.zst')
    shutil.rmtree(td);return o
raw=sizes(D);ax=sizes(R);rb=min(raw.values());ab=min(ax.values());res={'category':'csv_graph_v5','original':len(D),'representation':len(R),'raw':raw,'axiom':ax,'raw_best':rb,'axiom_best':ab,'win_pct':round((rb-ab)*100/rb,2),'exact':exact,'pack_s':round(pack_s,2)}
print('RESULT',json.dumps(res),flush=True);open(os.path.join(OUT,'beast_results.json'),'w').write(json.dumps(res,indent=2))
