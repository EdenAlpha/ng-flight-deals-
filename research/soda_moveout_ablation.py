import json, os, struct, sys
import numpy as np

# Reuse the exact audited container/decoder implementation from the pilot,
# but suppress its CLI tail so this file controls the experiment matrix.
src=open('research/soda_moveout_pilot.py').read().split('\nbench(sys.argv[1])')[0]
exec(compile(src,'soda_moveout_pilot.py','exec'),globals())
CORR_NEW=corr_options

def corr_old(Q):
    cand=[]
    for mode,K in [(0,Q),(1,diff1(Q,1))]:
        dc,a=pack_int(K); cand.append((len(a),mode,0,dc,a,b'',float(np.mean(K!=0))))
        if mode==1:
            m=K!=0; mz=ZC.compress(np.packbits(m.ravel(),bitorder='little').tobytes()); dc2,v=pack_int(K[m]); cand.append((len(mz)+len(v),mode,1,dc2,mz,v,float(m.mean())))
    return min(cand,key=lambda x:x[0])

def load_ablation(path):
    # Start with the exact pilot loader for receiver and offset layouts.
    X,layouts,extra,dt,geom=load(path)
    # Add PR101-style lexicographic receiver-coordinate ordering, still split by component.
    import segyio
    with segyio.open(path,'r',ignore_geometry=True) as f:
        gx=np.asarray(f.attributes(segyio.TraceField.GroupX)[:],np.float64)
        gy=np.asarray(f.attributes(segyio.TraceField.GroupY)[:],np.float64)
        sx=np.asarray(f.attributes(segyio.TraceField.SourceX)[:],np.float64)
        sy=np.asarray(f.attributes(segyio.TraceField.SourceY)[:],np.float64)
        try:sc=np.asarray(f.attributes(segyio.TraceField.SourceGroupScalar)[:],np.float64)
        except Exception:sc=np.ones(len(X),np.float64)
    scale=coord_scale(sc);gx*=scale;gy*=scale;sx*=scale;sy*=scale
    groups={}
    for i,(x,y) in enumerate(zip(gx,gy)):
        if x==0 and y==0:continue
        groups.setdefault((round(float(x),6),round(float(y),6)),[]).append(i)
    keys=list(groups); counts=np.array([len(v) for v in groups.values()]); C=int(np.bincount(counts).argmax())
    src=np.array([np.median(sx[np.isfinite(sx)&(sx!=0)]),np.median(sy[np.isfinite(sy)&(sy!=0)])])
    o=np.lexsort((np.array([k[0] for k in keys]),np.array([k[1] for k in keys])))
    rec=np.asarray(keys,float); off=np.linalg.norm(rec-src,axis=1)
    panels=[];offs=[]
    for c in range(C):
        ids=[groups[keys[j]][c] for j in o];panels.append(X[np.asarray(ids)]);offs.append(off[o])
    layouts['lexgeo']=(panels,offs)
    return X,layouts,extra,dt,geom

def run(path):
    X,layouts,extra,dt,geom=load_ablation(path);std=float(X.astype(np.float64).std());eps=.1*std;raw=X.nbytes
    sb,se=sz3_bytes(X,eps);extra_bytes=extra_err=0
    if extra.size:extra_bytes,extra_err=sz3_bytes(extra,eps)
    rows=[];B=512
    for lname,(panels,offs) in layouts.items():
      # Fair SZ3 on each component split/order too.
      szb=sze=0
      for p in panels:
        b,e=sz3_bytes(p,eps);szb+=b;sze=max(sze,e)
      szb+=extra_bytes;sze=max(sze,extra_err)
      rows.append({'kind':'sz3_layout','layout':lname,'bytes':szb,'ratio':raw/szb,'maxerr':sze,'valid':bool(sze<=eps*(1+5e-6))})
      for v in [0.,1200.]:
        vidx=VELS.index(v);allspec=[]
        for panel,off in zip(panels,offs):
            Y=warp_forward(panel,off,dt,v);spec=[]
            for t0 in range(0,Y.shape[1],B):
                m=min(B,Y.shape[1]-t0);W=np.zeros((Y.shape[0],B),np.float32);W[:,:m]=Y[:,t0:t0+m];spec.append(fwd(W))
            allspec.append(spec)
        for frac in [.00025,.0005,.001,.002]:
          for cname,cfn in [('old',corr_old),('new',CORR_NEW)]:
            globals()['corr_options']=cfn
            blobs=[];met=[];me=0.
            for panel,off,spec in zip(panels,offs,allspec):
                b,m=encode_panel(panel,off,dt,eps,B,frac,vidx,spec);R=decode_panel(b,off,dt,eps);me=max(me,float(np.max(np.abs(panel-R))));blobs.append(b);met.append(m)
            total=32+sum(map(len,blobs))+extra_bytes
            row={'kind':'codec','layout':lname,'velocity_mps':v,'frac':frac,'correction':cname,'bytes':total,'ratio':raw/total,'maxerr':max(me,extra_err),'valid':bool(max(me,extra_err)<=eps*(1+5e-6)),'model_bytes':sum(m['model_bytes'] for m in met),'corr_bytes':sum(m['corr_bytes'] for m in met),'extra_bytes':extra_bytes,'event_fraction':float(np.mean([m['event_fraction'] for m in met]))}
            rows.append(row);print('ROW',json.dumps(row),flush=True)
    globals()['corr_options']=CORR_NEW
    rows.sort(key=lambda r:r['ratio'],reverse=True)
    out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'std':std,'eps':eps,'geometry':geom,'direct_sz3':{'bytes':sb,'ratio':raw/sb,'maxerr':se},'top':rows}
    json.dump(out,open('soda_moveout_ablation.json','w'),indent=2)
    print('TOP',json.dumps(rows[:20],indent=2),flush=True)

run(sys.argv[1])
