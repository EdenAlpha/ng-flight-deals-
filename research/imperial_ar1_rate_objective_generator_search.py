import json,sys,math
import h5py,numpy as np
from numba import njit
import imperial_fair_ar_coarse_mixture_container as cm
import imperial_fair_ar_coarse_prefix_container as fair
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

A=cm.a
STEP=267
COMMON_HEADER=fair.COMMON_HEADER
SLOPE_DELTAS=(-.05,-.03,-.02,-.015,-.01,-.0075,-.005,-.003,-.002,-.0015,-.001,-.0005,0,.0005,.001,.0015,.002,.003,.005,.0075,.01,.015,.02,.03,.05)
BIAS_DELTAS=(-256,-128,-64,-32,-16,-8,-4,0,4,8,16,32,64,128,256)
EXACT_LIMIT=22

@njit(cache=True)
def build_ab(X,a,b,step):
    nc,nt=X.shape
    R=np.zeros((nc,nt),np.int32);K=np.zeros((nc,nt),np.int32)
    for c in range(nc):
        for t in range(nt):
            pred=0 if t==0 else int(np.rint(b+a*float(R[c,t-1])))
            k=int(np.rint((float(X[c,t])-pred)/step))
            R[c,t]=pred+step*k;K[c,t]=k
    return R,K

def proxy_bytes(K):
    u=m.zig(K);n=u.size;mx=int(u.max()) if n else 0;nb=max(1,mx.bit_length());bits=0.0
    for bit in range(nb):
        B=((u>>bit)&1).astype(np.uint8);o=int(B.sum());p=(o+.5)/(n+1.0)
        hg=-(p*math.log2(p)+(1-p)*math.log2(1-p))*n
        best=hg
        for axis in (0,1):
            prev=B[:-1,:] if axis==0 else B[:,:-1];cur=B[1:,:] if axis==0 else B[:,1:];s=0.0
            for pv in (0,1):
                q=prev==pv;nn=int(q.sum())
                if not nn:continue
                oo=int(cur[q].sum());pp=(oo+.5)/(nn+1.0)
                s-=nn*(pp*math.log2(pp)+(1-pp)*math.log2(1-pp))
            best=min(best,s+8.0)
        bits+=best
    return bits/8.0

def keycoef(a,b):
    q=np.asarray([a,b],np.float32)
    return (int(q.view(np.uint32)[0]),int(q.view(np.uint32)[1]))

def evaluate_screen(X,a,b,eps,stage):
    q=np.asarray([a,b],np.float32);aa=float(q[0]);bb=float(q[1]);R,K=build_ab(X,aa,bb,STEP)
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('screen hard',aa,bb,me,eps))
    return {'a':aa,'b':bb,'stage':stage,'proxy_bytes':proxy_bytes(K),'maxerr':me,'K':K}

def exact(X,eps,row):
    co=np.asarray([row['a'],row['b']],np.float32);model,mname=fair.encode_model(co);cod,pos=fair.decode_model(model,0,2)
    if pos!=len(model):raise RuntimeError('model trailing')
    R,K=build_ab(X,float(cod[0]),float(cod[1]),STEP);me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('exact hard',row['a'],row['b'],me,eps))
    field,_,Kd,detail=A.hybrid_frame(K)
    if not np.array_equal(Kd,K):raise RuntimeError('K replay')
    Rd=np.zeros_like(R)
    for c in range(K.shape[0]):
        for t in range(K.shape[1]):
            pred=0 if t==0 else int(np.rint(float(cod[1])+float(cod[0])*float(Rd[c,t-1])))
            Rd[c,t]=pred+STEP*int(Kd[c,t])
    if not np.array_equal(Rd,R):raise RuntimeError('R replay')
    mer=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if mer>eps*(1+5e-6):raise RuntimeError(('decode hard',mer,eps))
    return {'a':float(cod[0]),'b':float(cod[1]),'stage':row['stage'],'bytes':COMMON_HEADER+1+len(model)+int(field),
            'field_bytes':int(field),'model_bytes':len(model),'model_rep':mname,'proxy_bytes':row['proxy_bytes'],
            'legacy_bytes':row.get('legacy_bytes'),'maxerr':mer,'k_zero_fraction':float(np.mean(K==0)),'k_std':float(K.std()),'field_detail':detail}

def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std
        X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps)
    base=np.asarray(fair.fit(X,1,'prefix64'),np.float32);a0=float(base[0]);b0=float(base[1])
    # compile before timing/search
    build_ab(X,a0,b0,STEP)
    seen={};grid=[]
    for da in SLOPE_DELTAS:
        for db in BIAS_DELTAS:
            r=evaluate_screen(X,a0+da,b0+db,eps,'coarse_grid');k=keycoef(r['a'],r['b'])
            if k not in seen:seen[k]=r;grid.append(r)
    # Legacy exact-byte codec is a second independent cheap screen.
    for r in sorted(grid,key=lambda z:z['proxy_bytes'])[:70]:r['legacy_bytes']=int(m.encode_k(r['K'])[0])
    anchors=sorted([r for r in grid if r.get('legacy_bytes') is not None],key=lambda z:(z['legacy_bytes'],z['proxy_bytes']))[:10]
    refine=[]
    for q in anchors:
        for da in (-.001,-.0005,-.00025,-.000125,0,.000125,.00025,.0005,.001):
            for db in (-8,-4,-2,-1,0,1,2,4,8):
                r=evaluate_screen(X,q['a']+da,q['b']+db,eps,'refine');k=keycoef(r['a'],r['b'])
                if k in seen:continue
                seen[k]=r;refine.append(r)
    pool=grid+refine
    for r in sorted(refine,key=lambda z:z['proxy_bytes'])[:90]:r['legacy_bytes']=int(m.encode_k(r['K'])[0])
    byproxy=sorted(pool,key=lambda z:z['proxy_bytes'])[:12]
    bylegacy=sorted([r for r in pool if r.get('legacy_bytes') is not None],key=lambda z:(z['legacy_bytes'],z['proxy_bytes']))[:14]
    basekey=keycoef(a0,b0);selected={keycoef(r['a'],r['b']):r for r in byproxy+bylegacy}
    if basekey not in selected:selected[basekey]=seen.get(basekey,evaluate_screen(X,a0,b0,eps,'baseline'))
    finalists=sorted(selected.values(),key=lambda z:(z.get('legacy_bytes',10**12),z['proxy_bytes']))[:EXACT_LIMIT]
    exact_rows=[]
    for i,r in enumerate(finalists):
        er=exact(X,eps,r);exact_rows.append(er);print(json.dumps({k:v for k,v in er.items() if k!='field_detail'},indent=2),flush=True)
    exact_rows.sort(key=lambda z:z['bytes']);best=exact_rows[0]
    base_exact=next((r for r in exact_rows if keycoef(r['a'],r['b'])==basekey),None)
    if base_exact is None:
        br=evaluate_screen(X,a0,b0,eps,'baseline');base_exact=exact(X,eps,br);exact_rows.append(base_exact);exact_rows.sort(key=lambda z:z['bytes']);best=exact_rows[0]
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'step':STEP,'base_coef':[a0,b0],
         'coarse_grid_count':len(grid),'refine_count':len(refine),'screened_count':len(pool),'exact_count':len(exact_rows),
         'common_header_bytes':COMMON_HEADER,'sz3':{'bytes':int(szb),'orientation':ori},'baseline':base_exact,'exact_rows':exact_rows,'best':best,
         'scope':'NOVA computation-for-communication search over the transmitted AR1 coordinate system. The usual AR1/prefix64 least-squares coefficients are only a baseline. Hundreds of float32 slope/intercept pairs around that point are encoder-searched because predictor quality is not the objective: step267 nearest reconstruction preserves the unchanged hard bound for every candidate. Cheap empirical causal-bit and legacy-codec screens allocate compute only; they never decide the result. Finalists serialize/decode their exact float32 model, materialize the full coarse-prefix+mixture K address, independently K-decode and causally replay the source. Search path is not transmitted. Winner is actual total bytes only.'}
    json.dump(out,open('imperial_ar1_rate_objective_generator_search.json','w'),indent=2)
    print(json.dumps({'summary':{'baseline':base_exact['bytes'],'best':best['bytes'],'delta':best['bytes']-base_exact['bytes'],'base_coef':[a0,b0],'best_coef':[best['a'],best['b']],'model':best['model_bytes'],'field':best['field_bytes'],'sz3':int(szb),'gain_vs_sz3':szb/best['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
