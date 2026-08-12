import json,os,sys,struct
import numpy as np
src=open('research/soda_moveout_pilot.py').read().split('\nbench(sys.argv[1])')[0]
exec(compile(src,'soda_moveout_pilot.py','exec'),globals())

def zero_panel(panel,eps):
    Q=np.rint(panel/(2*eps)).astype(np.int32);_,cm,sp,dc,ca,cb,event=corr_options(Q)
    # Self-describing zero-model panel: nr,nt,mode,sparse,dtype,lengths + streams.
    h=struct.pack('<IIBBBQQ',panel.shape[0],panel.shape[1],cm,sp,dc,len(ca),len(cb));blob=h+ca+cb
    nr,nt,cm2,sp2,dc2,la,lb=struct.unpack('<IIBBBQQ',blob[:struct.calcsize('<IIBBBQQ')]);p=struct.calcsize('<IIBBBQQ');a=blob[p:p+la];b=blob[p+la:p+la+lb];total=nr*nt
    if sp2:
        mask=np.unpackbits(np.frombuffer(ZD.decompress(a),np.uint8),bitorder='little',count=total).astype(bool);vv=unpack_int(b,dc2,int(mask.sum()));K=np.zeros(total,np.int32);K[mask]=vv;K=K.reshape(nr,nt)
    else:K=unpack_int(a,dc2,total).reshape(nr,nt)
    R=corr_inverse(K,cm2).astype(np.float32)*np.float32(2*eps)
    return blob,R,{'N':0,'model_bytes':len(h),'corr_bytes':len(ca)+len(cb),'event_fraction':event}

def run(path):
    X,layouts,extra,dt,geom=load(path);std=float(X.astype(np.float64).std());eps=.1*std;raw=X.nbytes;extra_bytes=extra_err=0
    if extra.size:extra_bytes,extra_err=sz3_bytes(extra,eps)
    panels,offs=layouts['receiver'];B=512;M=panels[0].shape[0]*(B//2+1);rows=[]
    for v in [0.,1200.]:
        vidx=VELS.index(v);allspec=[]
        for panel,off in zip(panels,offs):
            Y=warp_forward(panel,off,dt,v);spec=[]
            for t0 in range(0,Y.shape[1],B):
                m=min(B,Y.shape[1]-t0);W=np.zeros((Y.shape[0],B),np.float32);W[:,:m]=Y[:,t0:t0+m];spec.append(fwd(W))
            allspec.append(spec)
        for N in range(0,9):
            blobs=[];met=[];me=0.
            for panel,off,spec in zip(panels,offs,allspec):
                if N==0:
                    b,R,m=zero_panel(panel,eps)
                else:
                    frac=N/M;b,m=encode_panel(panel,off,dt,eps,B,frac,vidx,spec);R=decode_panel(b,off,dt,eps)
                me=max(me,float(np.max(np.abs(panel-R))));blobs.append(b);met.append(m)
            total=32+sum(map(len,blobs))+extra_bytes;row={'velocity_state':v,'N_per_block':N,'bytes':total,'ratio':raw/total,'maxerr':max(me,extra_err),'valid':bool(max(me,extra_err)<=eps*(1+5e-6)),'model_bytes':sum(m['model_bytes'] for m in met),'corr_bytes':sum(m['corr_bytes'] for m in met),'extra_bytes':extra_bytes,'event_fraction':float(np.mean([m['event_fraction'] for m in met]))};rows.append(row);print('ROW',json.dumps(row),flush=True)
    rows.sort(key=lambda r:r['ratio'],reverse=True);out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'std':std,'eps':eps,'spectral_cells_per_block':M,'geometry':geom,'top':rows};json.dump(out,open('soda_moveout_exactN.json','w'),indent=2);print('BEST',json.dumps(rows,indent=2),flush=True)
run(sys.argv[1])
