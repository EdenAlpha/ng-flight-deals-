import json, os, time
import numpy as np
from pysz import sz,szConfig,szErrorBoundMode
meta=json.load(open('data/forge_subcube_meta.json'))
X=np.fromfile('data/forge_subcube_f32.bin','<f4').reshape(meta['shape'])
eps=float(meta['eps_10pct_std']);raw=X.nbytes

def comp_bytes(A,e):
    A=np.ascontiguousarray(A,dtype=np.float32)
    c=szConfig();c.errorBoundMode=szErrorBoundMode.ABS;c.absErrorBound=float(e)
    b,_=sz.compress(A,c)
    return int(b.size),b

def decode(b,shape):
    D,_=sz.decompress(b,np.float32,shape);return D

def neigh(A,axis,d):
    if d<0:
        sl=[slice(None)]*3;sl[axis]=slice(0,-1)
        edge=[slice(None)]*3;edge[axis]=slice(0,1)
        return np.concatenate([A[tuple(edge)],A[tuple(sl)]],axis=axis)
    sl=[slice(None)]*3;sl[axis]=slice(1,None)
    edge=[slice(None)]*3;edge[axis]=slice(-1,None)
    return np.concatenate([A[tuple(sl)],A[tuple(edge)]],axis=axis)

def candidate_full(Y,kind,delta,phase=0.0):
    lo=X-delta;hi=X+delta
    if kind=='zero':P=np.zeros_like(Y)
    elif kind=='time':P=.5*(neigh(Y,2,-1)+neigh(Y,2,1))
    elif kind=='space':P=.25*(neigh(Y,0,-1)+neigh(Y,0,1)+neigh(Y,1,-1)+neigh(Y,1,1))
    elif kind=='all':P=(2*Y+neigh(Y,0,-1)+neigh(Y,0,1)+neigh(Y,1,-1)+neigh(Y,1,1)+2*neigh(Y,2,-1)+2*neigh(Y,2,1))/10.0
    elif kind=='median':P=np.median(np.stack([Y,neigh(Y,2,-1),neigh(Y,2,1),neigh(Y,0,-1),neigh(Y,0,1),neigh(Y,1,-1),neigh(Y,1,1)]),axis=0)
    elif kind=='lattice':
        q=2*delta
        P=phase+np.rint((X-phase)/q)*q
    elif kind=='time_cubic':
        tm1=neigh(Y,2,-1);tp1=neigh(Y,2,1);tm2=neigh(tm1,2,-1);tp2=neigh(tp1,2,1)
        P=(-tm2+9*tm1+9*tp1-tp2)/16.0
    else:raise ValueError(kind)
    return np.clip(P,lo,hi).astype(np.float32)

def apply_block(dst,src,sl):
    out=dst.copy();out[sl]=src[sl];return out

def blocks(shape,bs):
    bi,bj,bt=bs
    for i in range(0,shape[0],bi):
      for j in range(0,shape[1],bj):
       for t in range(0,shape[2],bt):
        yield (slice(i,min(i+bi,shape[0])),slice(j,min(j+bj,shape[1])),slice(t,min(t+bt,shape[2])))

base_size,base_b=comp_bytes(X,eps);base_D=decode(base_b,X.shape)
print('DIRECT',json.dumps({'bytes':base_size,'ratio':raw/base_size,'maxerr':float(np.max(np.abs(X-base_D)))}),flush=True)
all_results=[]
for df in [.2,.35,.5,.65]:
    delta=df*eps;e2=eps-delta;Y=X.copy();cur,_=comp_bytes(Y,e2);start=cur
    print('START',json.dumps({'df':df,'eps2':e2,'bytes':cur,'ratio':raw/cur}),flush=True)
    history=[]
    stages=[((32,32,128),['zero','time','space','all','median','time_cubic','lattice']),((16,16,64),['zero','time','space','all','lattice'])]
    for stage,(bs,kinds) in enumerate(stages):
        # freeze candidate fields at start of each block decision from current Y; candidates remain legal wrt original X.
        naccept=0;tested=0
        for sl in blocks(X.shape,bs):
            best_bytes=cur;best_block=None;best_name='keep'
            # create local candidate fields on demand. Lattice gets four phase options.
            specs=[]
            for kind in kinds:
                if kind=='lattice':
                    q=2*delta
                    specs += [('lattice',p*q/4.0) for p in range(4)]
                else:specs.append((kind,0.0))
            # full candidate field needed for neighborhood-aware operations; recompute only each kind.
            cache={}
            for kind,phase in specs:
                key=(kind,phase)
                if key not in cache:cache[key]=candidate_full(Y,kind,delta,phase)
                T=Y.copy();T[sl]=cache[key][sl]
                nb,_=comp_bytes(T,e2);tested+=1
                if nb<best_bytes:
                    best_bytes=nb;best_block=np.array(T[sl],copy=True);best_name=f'{kind}:{phase:.6g}'
            if best_block is not None:
                Y[sl]=best_block;cur=best_bytes;naccept+=1
                print('ACCEPT',json.dumps({'df':df,'stage':stage,'bs':bs,'block':[sl[0].start,sl[1].start,sl[2].start],'choice':best_name,'bytes':cur,'ratio':raw/cur}),flush=True)
        history.append({'stage':stage,'bs':bs,'accepted':naccept,'tested':tested,'bytes':cur,'ratio':raw/cur})
        print('STAGE',json.dumps(history[-1]),flush=True)
    final_bytes,final_b=comp_bytes(Y,e2);D=decode(final_b,Y.shape);final_err=float(np.max(np.abs(X-D)));morph=float(np.max(np.abs(X-Y)))
    tag=str(df).replace('.','p');Y.astype('<f4').tofile(f'forge_shaped_{tag}.bin')
    row={'delta_frac':df,'start_bytes':start,'bytes':final_bytes,'ratio':raw/final_bytes,'morph_max':morph,'final_maxerr':final_err,'history':history,'shaped_file':f'forge_shaped_{tag}.bin'}
    all_results.append(row);print('FINAL',json.dumps(row),flush=True)
all_results.sort(key=lambda r:r['bytes'])
open('forge_codec_inloop_results.json','w').write(json.dumps({'direct':{'bytes':base_size,'ratio':raw/base_size},'eps':eps,'raw':raw,'results':all_results},indent=2))
print('BEST',json.dumps(all_results,indent=2),flush=True)
