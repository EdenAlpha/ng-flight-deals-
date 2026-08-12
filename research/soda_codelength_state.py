import itertools,json,math,os,struct,sys
import numpy as np
from numba import njit

# Reuse the already-audited Soda geometry map and exact byte coders.
src=open('research/soda_grid_lattice.py').read().split('\ndef main(path):')[0]
exec(compile(src,'soda_grid_lattice.py','exec'),globals())
s2=open('research/soda_grid_sparse.py').read().split('\npath=sys.argv[1]')[0]
exec(compile(s2,'soda_grid_sparse.py','exec'),globals())

@njit(cache=True)
def trans_cost(d,event_cost,exception_cost,mag_cost):
    if d==0:
        return 0.0
    a=abs(d)
    c=event_cost
    if a>1:
        c += exception_cost + mag_cost*math.log2(float(a))
    return c

@njit(cache=True)
def codelength_trace(x,eps,step,event_cost,exception_cost,mag_cost):
    # Exact shortest path through all legal integer reconstruction states.
    # Unlike PR #131, the objective is not minimum transition count: it trades
    # event support cost against the much cheaper +/-1 symbols and larger jumps.
    n=x.size
    lo=np.empty(n,np.int32);hi=np.empty(n,np.int32);maxw=0
    for t in range(n):
        xd=float(x[t])
        L=int(math.ceil((xd-eps)/step-1e-12));H=int(math.floor((xd+eps)/step+1e-12))
        if L>H:
            raise ValueError('empty legal state set')
        lo[t]=L;hi[t]=H
        w=H-L+1
        if w>maxw:maxw=w
    back=np.zeros((n,maxw),np.uint8)
    inf=1e300
    prev=np.empty(maxw,np.float64);cur=np.empty(maxw,np.float64)
    w0=hi[0]-lo[0]+1
    for j in range(maxw):prev[j]=inf
    for j in range(w0):
        q=lo[0]+j
        prev[j]=trans_cost(q,event_cost,exception_cost,mag_cost)
    for t in range(1,n):
        wp=hi[t-1]-lo[t-1]+1;wc=hi[t]-lo[t]+1
        for j in range(maxw):cur[j]=inf
        for j in range(wc):
            qc=lo[t]+j;best=inf;bi=0
            for k in range(wp):
                qp=lo[t-1]+k
                v=prev[k]+trans_cost(qc-qp,event_cost,exception_cost,mag_cost)
                if v<best:
                    best=v;bi=k
            cur[j]=best;back[t,j]=bi
        tmp=prev;prev=cur;cur=tmp
    wn=hi[n-1]-lo[n-1]+1;j=0;best=prev[0]
    for k in range(1,wn):
        if prev[k]<best:best=prev[k];j=k
    q=np.empty(n,np.int32)
    for t in range(n-1,-1,-1):
        q[t]=lo[t]+j
        if t>0:j=int(back[t,j])
    me=0.0
    for t in range(n):
        e=abs(float(x[t])-float(q[t])*step)
        if e>me:me=e
    if me>eps*(1+1e-10):raise ValueError('legal reconstruction failure')
    return q,best

def build_states(X,tm,outids,shape,eps,step,event_cost,exception_cost,mag_cost):
    G=np.zeros(shape,np.int32);objective=0.0
    for tid,c,l,s in tm:
        q,cost=codelength_trace(X[tid],eps,step,event_cost,exception_cost,mag_cost);G[c,l,s]=q;objective+=cost
    O=np.empty((len(outids),X.shape[1]),np.int32)
    for j,tid in enumerate(outids.tolist()):
        q,cost=codelength_trace(X[tid],eps,step,event_cost,exception_cost,mag_cost);O[j]=q;objective+=cost
    return G,O,objective

def best_main(K):
    rows=[]
    for level in (19,22):
      for perm in itertools.permutations(range(4)):
       for rep in (0,1,2):
        b=encode_array(K,perm,rep,level);R=decode_array(b)
        if not np.array_equal(R,K):raise RuntimeError('main decode')
        rows.append((len(b),level,perm,rep,b))
    rows.sort(key=lambda x:x[0])
    return rows[0],[{'bytes':x[0],'level':x[1],'perm':list(x[2]),'rep':['raw','sparse','ternary'][x[3]]} for x in rows[:8]]

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
    rows.sort(key=lambda x:x[0])
    return rows[0],[{'bytes':x[0],'tdiff':x[1],'level':x[2],'perm':list(x[3]),'rep':['raw','sparse','ternary'][x[4]]} for x in rows[:6]]

def run(path,event_cost,exception_cost,mag_cost=1.0):
    X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());public_eps=.1*std;eps=public_eps*(1-2e-4);step=eps;raw=X.nbytes
    G0,tm,outids,geom=geometry_map(X,gx,gy);G,O,obj=build_states(X,tm,outids,G0.shape,eps,step,event_cost,exception_cost,mag_cost);K=delta(G,3)
    bm,mc=best_main(K);bo,oc=best_out(O);mb=bm[4];ob=bo[5]
    fmt='<8sdddfffQQ';h=struct.pack(fmt,b'CLSTATE1',public_eps,eps,step,float(event_cost),float(exception_cost),float(mag_cost),len(mb),len(ob));blob=h+mb+ob
    p=struct.calcsize(fmt);_,pe,ee,ss,ce,cx,cm,lm,lo=struct.unpack(fmt,blob[:p]);RK=decode_array(blob[p:p+lm]);ROA=decode_out_sparse(blob[p+lm:p+lm+lo]);RG=undelta(RK,3);RO=undelta(ROA,1) if bo[1] else ROA
    recon=np.empty_like(X)
    for tid,c,l,s in tm:recon[tid]=RG[c,l,s].astype(np.float32)*np.float32(ss)
    recon[outids]=RO.astype(np.float32)*np.float32(ss);me=float(np.max(np.abs(X-recon)));szb,sze=sz3_bytes(X,public_eps)
    vals,cnt=np.unique(K,return_counts=True);ix=np.argsort(cnt)[::-1][:10]
    return {'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'public_eps':public_eps,'internal_eps':eps,'step_fraction':1.0,'geometry':geom,'objective':{'event_cost':event_cost,'exception_cost':exception_cost,'magnitude_cost':mag_cost,'proxy_total':obj},'K_nonzero_fraction':float(np.mean(K!=0)),'K_top_values':[{'v':int(vals[i]),'count':int(cnt[i])} for i in ix],'main_best':mc[0],'main_candidates':mc,'outlier_best':oc[0],'container_bytes':len(blob),'ratio':raw/len(blob),'maxerr':me,'valid':bool(me<=public_eps),'sz3':{'bytes':szb,'ratio':raw/szb,'maxerr':sze},'gain_over_sz3':(raw/len(blob))/(raw/szb)}

path=sys.argv[1]
# Precommitted small objective dictionary. These interpolate between nearest-state
# behavior and the failed minimum-transition extreme from PR #131.
configs=[(3.0,1.0),(4.5,1.5),(6.0,2.0),(8.0,4.0)]
rows=[]
for ce,cx in configs:
    print('OBJECTIVE',ce,cx,flush=True);r=run(path,ce,cx);rows.append(r);print(json.dumps({'event_cost':ce,'exception_cost':cx,'ratio':r['ratio'],'bytes':r['container_bytes'],'K_nonzero_fraction':r['K_nonzero_fraction'],'gain':r['gain_over_sz3'],'maxerr':r['maxerr']},indent=2),flush=True)
rows.sort(key=lambda r:r['container_bytes']);json.dump({'best':rows[0],'all':rows},open('soda_codelength_state.json','w'),indent=2)
