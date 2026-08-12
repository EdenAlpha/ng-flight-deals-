import json,sys,math
import h5py,numpy as np,zstandard as zstd,maxflow
from pysz import sz,szConfig,szErrorBoundMode

C=128;T=1024;SAFETY=1-1e-5;HFACTOR=1.001
Z=zstd.ZstdCompressor(level=19)

def stats(d):
    s=ss=0.;n=0
    for i in range(0,d.shape[0],2048):
        x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
    m=s/n;return m,float(np.sqrt(max(0,ss/n-m*m)))

def szrun(x,eps):
    best=None
    for tr in (False,True):
        a=np.ascontiguousarray((x.T if tr else x).astype(np.float32));cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
        b,_=sz.compress(a,cfg);r,_=sz.decompress(b,np.float32,a.shape);me=float(np.max(np.abs(a-r)))
        if me>eps*(1+5e-6):raise RuntimeError(('sz',me,eps))
        if best is None or int(b.size)<best:best=int(b.size)
    return best

def legal(X,bound,h):
    lo=np.ceil((X-bound)/h).astype(np.int32);hi=np.floor((X+bound)/h).astype(np.int32)
    if np.any(lo>hi):raise RuntimeError('empty legal set')
    if int(np.max(hi-lo))>1:raise RuntimeError(('not binary',int(np.max(hi-lo))))
    return lo,hi

def add_pair(g,u,v,a0,a1,b0,b1,w,unary):
    V00=w*abs(a0-b0);V01=w*abs(a0-b1);V10=w*abs(a1-b0);V11=w*abs(a1-b1)
    sub=V01+V10-V00-V11
    if sub < -1e-8:raise RuntimeError(('non-submodular',V00,V01,V10,V11))
    wc=max(0.0,sub*0.5)
    unary[u]+=V10-V00-wc;unary[v]+=V01-V00-wc
    if wc>0:g.add_edge(u,v,wc,wc)

def solve_tv(lo,hi,space_weight):
    n=lo.size;lf=lo.ravel();hf=hi.ravel();g=maxflow.Graph[float](n,2*n);g.add_nodes(n);unary=np.zeros(n,np.float64);ids=np.arange(n,dtype=np.int32).reshape(C,T)
    for c in range(C):
        for t in range(T-1):
            u=int(ids[c,t]);v=int(ids[c,t+1]);add_pair(g,u,v,int(lf[u]),int(hf[u]),int(lf[v]),int(hf[v]),1.0,unary)
    for c in range(C-1):
        for t in range(T):
            u=int(ids[c,t]);v=int(ids[c+1,t]);add_pair(g,u,v,int(lf[u]),int(hf[u]),int(lf[v]),int(hf[v]),float(space_weight),unary)
    for i,u in enumerate(unary):
        if u>=0:g.add_tedge(i,float(u),0.0)
        else:g.add_tedge(i,0.0,float(-u))
    flow=float(g.maxflow());lab=np.fromiter((g.get_segment(i) for i in range(n)),dtype=np.int8,count=n)
    return np.where(lab.reshape(C,T)==0,lo,hi).astype(np.int32),flow

def pack_candidates(q):
    cand=[]
    def comp(name,a):
        mn=int(a.min());mx=int(a.max())
        for dt in (np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4')):
            if mn>=np.iinfo(dt).min and mx<=np.iinfo(dt).max:
                cand.append((len(Z.compress(np.ascontiguousarray(a).astype(dt).tobytes()))+32,name+'_'+dt.str));break
    comp('raw',q);dt=q.copy();dt[:,1:]-=q[:,:-1];comp('dt',dt);dc=q.copy();dc[1:]-=q[:-1];comp('dc',dc)
    L=q.copy();L[1:,1:]=q[1:,1:]-q[:-1,1:]-q[1:,:-1]+q[:-1,:-1];comp('lorenzo',L)
    off=(q.astype(np.int64)-int(q.min())).astype(np.uint32);nb=max(1,int(off.max()).bit_length());tot=64
    for b in range(nb):tot+=len(Z.compress(np.packbits(((off>>b)&1).astype(np.uint8),bitorder='little').tobytes()))+8
    cand.append((tot,'offset_bitplanes'));return sorted(cand)

def H(a):
    _,c=np.unique(a,return_counts=True);p=c.astype(np.float64)/c.sum();return float(-(p*np.log2(p)).sum())

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=stats(d);eps=.1*std;bound=eps*SAFETY;h=bound*HFACTOR
        specs=[('center',14488,3392),('edge',14488,6784),('early',0,3392)];rows=[];szmap={}
        for name,t0,c0 in specs:
            X=np.asarray(d[t0:t0+T,c0:c0+C],np.float64).T;raw=X.size*2;sb=szrun(X,eps);szmap[name]=sb;lo,hi=legal(X,bound,h)
            for sw in (0.25,0.5,1.0,2.0,4.0):
                q,flow=solve_tv(lo,hi,sw);R=q.astype(np.float64)*h;me=float(np.max(np.abs(X-R)))
                if me>eps*(1+5e-6):raise RuntimeError(('hard error',name,sw,me,eps))
                packs=pack_candidates(q);best=packs[0]
                rows.append({'tile':name,'space_weight':sw,'mean_legal_states':float(np.mean(hi-lo+1)),'bytes':best[0],'rep':best[1],'all_reps':packs,'gain_vs_sz3':sb/best[0],'ratio_raw':raw/best[0],'bps':8*best[0]/X.size,'sz3_bps':8*sb/X.size,'maxerr':me,'flow_objective':flow,'time_change':float(np.mean(q[:,1:]!=q[:,:-1])),'space_change':float(np.mean(q[1:]!=q[:-1])),'H_q':H(q),'H_dt':H(np.diff(q,axis=1))})
        combos=[]
        for sw in (0.25,0.5,1.0,2.0,4.0):
            rr=[r for r in rows if r['space_weight']==sw];b=sum(r['bytes'] for r in rr);szb=sum(szmap[r['tile']] for r in rr);raw=2*C*T*len(rr)
            combos.append({'space_weight':sw,'bytes':b,'sz3_bytes':szb,'gain_vs_sz3':szb/b,'bps':8*b/(C*T*len(rr)),'ratio_raw':raw/b,'min_tile_gain':min(r['gain_vs_sz3'] for r in rr),'median_time_change':float(np.median([r['time_change'] for r in rr])),'median_space_change':float(np.median([r['space_change'] for r in rr])),'reps':[r['rep'] for r in rr]})
        combos.sort(key=lambda x:x['bytes']);out={'std':std,'eps':eps,'h':h,'h_over_eps':h/eps,'two_x_sz3_target_bps':1.8859028760018859,'combos':combos,'rows':rows,'scope':'Exact binary global 2-D total-variation minimization over every legal reconstruction choice via s-t min-cut; all final payload bytes are realizable Zstd/bitplane encodings; three precommitted tiles, no per-tile weight tuning in aggregate.'}
        print(json.dumps({'best':combos[:5]},indent=2),flush=True);json.dump(out,open('imperial_global_tv_codeword.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
