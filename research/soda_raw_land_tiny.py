import sys,json,os,numpy as np
src=open('research/soda_raw_land_fast.py').read().split("\nout={'shots':[]}")[0]
exec(compile(src,'soda_raw_land_fast.py','exec'),globals())
path=sys.argv[1];X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());eps=.1*std;raw=X.nbytes;ls,geom=layouts(X,gx,gy);rows=[];base=[]
for li,(lname,panels) in enumerate(ls.items()):
    sb,se=sz3_layout(panels,eps);base.append({'layout':lname,'bytes':sb,'ratio':raw/sb,'maxerr':se})
    for B in [512,1024]:
      for frac in [0.004,0.016,0.032]:
        blob,event=encode_layout(panels,eps,B,frac,li);R,_,_=decode_layout(blob);me=max(float(np.max(np.abs(a-b))) for a,b in zip(panels,R));row={'layout':lname,'B':B,'frac':frac,'bytes':len(blob),'ratio':raw/len(blob),'event_fraction':event,'maxerr':me,'valid':bool(me<=eps*(1+3e-6))};rows.append(row);print('ROW',row,flush=True)
rows.sort(key=lambda r:r['ratio'],reverse=True);base.sort(key=lambda r:r['ratio'],reverse=True);out={'file':os.path.basename(path),'shape':list(X.shape),'dt_us':dt,'raw_bytes':raw,'std':std,'eps':eps,'geometry':geom,'top':rows,'sz3':base};json.dump(out,open('soda_raw_tiny_result.json','w'),indent=2);print('RESULT',json.dumps({'best':rows[0],'sz3':base[0],'geometry':geom,'shape':list(X.shape)},indent=2),flush=True)
