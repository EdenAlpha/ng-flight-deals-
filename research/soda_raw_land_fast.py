import sys,json,os,struct,numpy as np
# Reuse the audited container/decoder definitions without executing its CLI tail.
src=open('research/soda_raw_land_topn.py').read().split('\nfiles=sys.argv[1:]')[0]
exec(compile(src,'soda_raw_land_topn.py','exec'),globals())

SPEC_CACHE={}
def encode_panel_cached(X,eps,B,frac):
    nr,nt=X.shape;nblk=(nt+B-1)//B;step=2.0*eps;key=(id(X),B)
    specs=SPEC_CACHE.get(key)
    if specs is None:
        specs=[]
        for b in range(nblk):
            t0=b*B;m=min(B,nt-t0);W=np.zeros((nr,B),np.float32);W[:,:m]=X[:,t0:t0+m];specs.append((fwd(W),m))
        SPEC_CACHE[key]=specs
    idxs=[];vals=[];scales=[];P=np.zeros_like(X);N=None
    for b,(F,m) in enumerate(specs):
        flat=F.reshape(-1);NN=max(1,min(flat.size,int(round(frac*flat.size))));N=NN if N is None else N
        if NN!=N:raise RuntimeError('N changed')
        ix=np.argpartition(np.abs(flat),-N)[-N:];ix=np.sort(ix).astype(np.uint32);v=flat[ix]
        comp=np.stack([v.real,v.imag],axis=1);sc=max(float(np.max(np.abs(comp)))/127.0,1e-30);sc16=np.float16(sc);sd=np.float32(sc16)
        q=np.clip(np.rint(comp/sd),-127,127).astype(np.int8);vq=(q[:,0].astype(np.float32)+1j*q[:,1].astype(np.float32))*sd
        fq=np.zeros(flat.size,np.complex64);fq[ix.astype(np.int64)]=vq;t0=b*B;R=inv(fq.reshape(F.shape),B);P[:,t0:t0+m]=R[:,:m]
        idxs.append(ix);vals.append(q);scales.append(sc16)
    iz=z(np.concatenate(idxs).astype('<u4',copy=False).tobytes());vz=z(np.concatenate(vals,axis=0).astype(np.int8,copy=False).tobytes());szb=z(np.asarray(scales,dtype='<f2').tobytes())
    Q=np.rint((X-P)/step).astype(np.int32);opts=[]
    dc,a=pack_int(Q);opts.append((len(a),0,dc,a,b''));K=Q.copy();K[:,1:]-=Q[:,:-1];dc,a=pack_int(K);opts.append((len(a),1,dc,a,b''))
    mask=K!=0;mz=z(np.packbits(mask.ravel(),bitorder='little').tobytes());dc,vv=pack_int(K[mask]);opts.append((len(mz)+len(vv),2,dc,mz,vv))
    _,cm,dc,ca,cb=min(opts,key=lambda q:q[0]);h=struct.pack(PANEL_HDR,nr,nt,B,N,nblk,cm,dc,len(iz),len(vz),len(szb),len(ca),len(cb))
    return h+iz+vz+szb+ca+cb,float(mask.mean())

encode_panel=encode_panel_cached

def bench_fast(path):
    X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());eps=.1*std;raw=X.nbytes;ls,geom=layouts(X,gx,gy);rows=[];baselines=[]
    for li,(lname,panels) in enumerate(ls.items()):
        sb,se=sz3_layout(panels,eps);baselines.append({'layout':lname,'bytes':sb,'ratio':raw/sb,'maxerr':se})
        for B in [512,1024,2048]:
            for frac in [0.002,0.004,0.008,0.016,0.032]:
                blob,event=encode_layout(panels,eps,B,frac,li);R,_,_=decode_layout(blob);me=max(float(np.max(np.abs(a-b))) for a,b in zip(panels,R));rows.append({'layout':lname,'B':B,'frac':frac,'bytes':len(blob),'ratio':raw/len(blob),'event_fraction':event,'maxerr':me,'valid':bool(me<=eps*(1+3e-6))});print('ROW',os.path.basename(path),rows[-1],flush=True)
    rows.sort(key=lambda r:r['ratio'],reverse=True);baselines.sort(key=lambda r:r['ratio'],reverse=True)
    return {'file':os.path.basename(path),'shape':list(X.shape),'dt_us':dt,'raw_bytes':raw,'std':std,'eps':eps,'geometry':geom,'top':rows[:20],'sz3':baselines}

out={'shots':[]}
for f in sys.argv[1:]:
    print('BENCH',f,flush=True);r=bench_fast(f);out['shots'].append(r);print('SHOTBEST',json.dumps({'file':r['file'],'best':r['top'][0],'sz3':r['sz3'][0]},indent=2),flush=True);SPEC_CACHE.clear()
json.dump(out,open('soda_raw_fast_results.json','w'),indent=2)
