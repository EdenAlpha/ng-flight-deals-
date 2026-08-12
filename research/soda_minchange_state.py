import itertools,json,os,struct,sys
import numpy as np
src=open('research/soda_grid_lattice.py').read().split('\ndef main(path):')[0]
exec(compile(src,'soda_grid_lattice.py','exec'),globals())
s2=open('research/soda_grid_sparse.py').read().split('\npath=sys.argv[1]')[0]
exec(compile(s2,'soda_grid_sparse.py','exec'),globals())

def minchange_trace(x,eps,step):
    # Integer q is legal iff x-eps <= q*step <= x+eps. Intersect consecutive
    # integer intervals; a new segment is provably necessary exactly when the
    # running intersection becomes empty.
    xd=x.astype(np.float64);lo=np.ceil((xd-eps)/step-1e-12).astype(np.int32);hi=np.floor((xd+eps)/step+1e-12).astype(np.int32)
    if np.any(lo>hi): raise RuntimeError('empty legal state set')
    n=x.size;segs=[];a=0;L=int(lo[0]);H=int(hi[0])
    for t in range(1,n):
        nL=max(L,int(lo[t]));nH=min(H,int(hi[t]))
        if nL<=nH:L,H=nL,nH
        else:segs.append((a,t,L,H));a=t;L=int(lo[t]);H=int(hi[t])
    segs.append((a,n,L,H));q=np.empty(n,np.int32);prev=None
    for a,b,L,H in segs:
        if prev is None:v=int(np.clip(0,L,H))
        else:v=int(np.clip(prev,L,H))
        q[a:b]=v;prev=v
    if np.max(np.abs(x.astype(np.float64)-q.astype(np.float64)*step))>eps*(1+1e-10):raise RuntimeError('legal reconstruction failure')
    return q,len(segs)

def build_states(X,tm,outids,shape,eps,step):
    G=np.zeros(shape,np.int32);seg_main=0
    for tid,c,l,s in tm:
        q,n=minchange_trace(X[tid],eps,step);G[c,l,s]=q;seg_main+=n
    O=np.empty((len(outids),X.shape[1]),np.int32);seg_out=0
    for j,tid in enumerate(outids.tolist()):
        q,n=minchange_trace(X[tid],eps,step);O[j]=q;seg_out+=n
    return G,O,seg_main,seg_out

def best_main(K):
    rows=[]
    for level in (19,22):
      for perm in itertools.permutations(range(4)):
       for rep in (0,1,2):
        b=encode_array(K,perm,rep,level);R=decode_array(b)
        if not np.array_equal(R,K):raise RuntimeError('main decode')
        rows.append((len(b),level,perm,rep,b))
    return min(rows,key=lambda x:x[0]),sorted([{'bytes':x[0],'level':x[1],'perm':list(x[2]),'rep':['raw','sparse','ternary'][x[3]]} for x in rows],key=lambda r:r['bytes'])[:10]
def best_out(O):
    rows=[]
    for td in (False,True):
      A=delta(O,1) if td else O
      for level in (19,22):
       for perm in ((0,1,2,3),(3,1,2,0)):
        for rep in (0,1,2):
         b=encode_out_sparse(A,perm,rep,level);R=decode_out_sparse(b);RR=undelta(R,1) if td else R
         if not np.array_equal(RR,O):raise RuntimeError('out decode')
         rows.append((len(b),td,level,perm,rep,b))
    return min(rows,key=lambda x:x[0]),sorted([{'bytes':x[0],'tdiff':x[1],'level':x[2],'perm':list(x[3]),'rep':['raw','sparse','ternary'][x[4]]} for x in rows],key=lambda r:r['bytes'])[:8]

def run(path,frac):
    X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());public_eps=.1*std;eps=public_eps*(1-2e-4);step=eps*frac;raw=X.nbytes
    G0,tm,outids,geom=geometry_map(X,gx,gy);G,O,sm,so=build_states(X,tm,outids,G0.shape,eps,step);K=delta(G,3)
    bm,mc=best_main(K);bo,oc=best_out(O);mb=bm[4];ob=bo[5]
    h=struct.pack('<8sdddQQ',b'MINCHG01',public_eps,eps,step,len(mb),len(ob));blob=h+mb+ob
    p=struct.calcsize('<8sdddQQ');_,pe,ee,ss,lm,lo=struct.unpack('<8sdddQQ',blob[:p]);RK=decode_array(blob[p:p+lm]);ROA=decode_out_sparse(blob[p+lm:p+lm+lo]);RG=undelta(RK,3);RO=undelta(ROA,1) if bo[1] else ROA
    recon=np.empty_like(X)
    for tid,c,l,s in tm:recon[tid]=RG[c,l,s].astype(np.float32)*np.float32(ss)
    recon[outids]=RO.astype(np.float32)*np.float32(ss);me=float(np.max(np.abs(X-recon)));szb,sze=sz3_bytes(X,public_eps)
    return {'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'public_eps':public_eps,'internal_eps':eps,'step_fraction':frac,'step':step,'geometry':geom,'main_segments':sm,'outlier_segments':so,'K_nonzero_fraction':float(np.mean(K!=0)),'main_best':mc[0],'main_candidates':mc,'outlier_best':oc[0],'container_bytes':len(blob),'ratio':raw/len(blob),'maxerr':me,'valid':bool(me<=public_eps),'sz3':{'bytes':szb,'ratio':raw/szb,'maxerr':sze},'gain_over_sz3':(raw/len(blob))/(raw/szb)}

path=sys.argv[1];fracs=[float(x) for x in sys.argv[2:]] or [1.0,.5];rows=[]
for f in fracs:
    print('STEP',f,flush=True);r=run(path,f);rows.append(r);print(json.dumps({'step_fraction':f,'ratio':r['ratio'],'bytes':r['container_bytes'],'K_nonzero_fraction':r['K_nonzero_fraction'],'gain':r['gain_over_sz3'],'maxerr':r['maxerr']},indent=2),flush=True)
rows.sort(key=lambda r:r['ratio'],reverse=True);json.dump({'best':rows[0],'all':rows},open('soda_minchange_state.json','w'),indent=2)
