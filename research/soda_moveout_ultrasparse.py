import json,os,sys
import numpy as np
src=open('research/soda_moveout_pilot.py').read().split('\nbench(sys.argv[1])')[0]
exec(compile(src,'soda_moveout_pilot.py','exec'),globals())

def run(path):
    X,layouts,extra,dt,geom=load(path);std=float(X.astype(np.float64).std());eps=.1*std;raw=X.nbytes;extra_bytes=extra_err=0
    if extra.size:extra_bytes,extra_err=sz3_bytes(extra,eps)
    panels,offs=layouts['receiver'];rows=[];B=512
    for v in [0.,1200.]:
        vidx=VELS.index(v);allspec=[]
        for panel,off in zip(panels,offs):
            Y=warp_forward(panel,off,dt,v);spec=[]
            for t0 in range(0,Y.shape[1],B):
                m=min(B,Y.shape[1]-t0);W=np.zeros((Y.shape[0],B),np.float32);W[:,:m]=Y[:,t0:t0+m];spec.append(fwd(W))
            allspec.append(spec)
        for frac in [0.000015625,0.00003125,0.0000625,0.000125,0.00025]:
            blobs=[];met=[];me=0.
            for panel,off,spec in zip(panels,offs,allspec):
                b,m=encode_panel(panel,off,dt,eps,B,frac,vidx,spec);R=decode_panel(b,off,dt,eps);me=max(me,float(np.max(np.abs(panel-R))));blobs.append(b);met.append(m)
            total=32+sum(map(len,blobs))+extra_bytes;row={'velocity_state':v,'frac':frac,'bytes':total,'ratio':raw/total,'maxerr':max(me,extra_err),'valid':bool(max(me,extra_err)<=eps*(1+5e-6)),'model_bytes':sum(m['model_bytes'] for m in met),'corr_bytes':sum(m['corr_bytes'] for m in met),'extra_bytes':extra_bytes,'event_fraction':float(np.mean([m['event_fraction'] for m in met]))};rows.append(row);print('ROW',json.dumps(row),flush=True)
    rows.sort(key=lambda r:r['ratio'],reverse=True);out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'std':std,'eps':eps,'geometry':geom,'top':rows};json.dump(out,open('soda_moveout_ultrasparse.json','w'),indent=2);print('BEST',json.dumps(rows,indent=2),flush=True)
run(sys.argv[1])
