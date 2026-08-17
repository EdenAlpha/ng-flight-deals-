import json,math,struct,sys
import h5py,numpy as np
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as ah
import imperial_huber_ar32_component_zsm_gps as cg
import imperial_gca_residue_codebook as rc

C=128;NT=30000;C0=512;STEP=267;RAD=133;INC=2468803;MATCHED_SZ3=2767977
FAMILIES=('hist','hist_p','hist_coord','all')
FIDS={x:i for i,x in enumerate(FAMILIES)}
COEFFS=(-32,-16,-8,-4,-2,-1,0,1,2,4,8,16,32)


def wrap(z):return ((np.asarray(z,dtype=np.int64)+RAD)%STEP)-RAD

def features_arrays(K,P):
    prev=np.zeros_like(K,dtype=np.int64);prev[:,1:]=K[:,:-1]
    prev2=np.zeros_like(K,dtype=np.int64);prev2[:,2:]=K[:,:-2]
    left=np.zeros_like(K,dtype=np.int64);left[1:]=K[:-1]
    pm=np.mod(P,STEP).astype(np.int64)
    cc=np.repeat(np.arange(C,dtype=np.int64)[:,None],NT,axis=1)
    tt=np.repeat((np.arange(NT,dtype=np.int64)%STEP)[None,:],C,axis=0)
    return [prev,prev2,left,pm,cc,tt]

def dims(f):return {'hist':3,'hist_p':4,'hist_coord':5,'all':6}[f]

def score(vals,Fs,coef):
    z=np.full(len(vals),int(coef[0]),np.int64)
    for j,F in enumerate(Fs):z+=int(coef[j+1])*F
    d=wrap(z);k=np.floor_divide(vals-d+RAD,STEP);return rc.proxy_cost_k(k)

def fit_law(N,K0,P0,fam):
    allF=features_arrays(K0,P0)[:dims(fam)]
    n=N.size;idx=np.linspace(0,n-1,min(250000,n),dtype=np.int64);vals=N.reshape(-1)[idx];Fs=[x.reshape(-1)[idx] for x in allF]
    co=np.zeros(len(Fs)+1,np.int16);hist=[]
    for it in range(3):
        changed=False
        for j in range(len(co)):
            best=(1e300,int(co[j]))
            for v in COEFFS:
                z=co.copy();z[j]=v;s=score(vals,Fs,z)
                if s<best[0]:best=(s,v)
            if best[1]!=int(co[j]):co[j]=best[1];changed=True
        s=score(vals,Fs,co);hist.append({'iter':it,'sample_proxy_bits':float(s),'coefficients':[int(x) for x in co]})
        if not changed:break
    return co,hist

def phase_scalar(fam,co,K,p,c,t):
    vals=[int(K[c,t-1]) if t else 0,int(K[c,t-2]) if t>1 else 0,int(K[c-1,t]) if c else 0,int(p)%STEP,c,t%STEP]
    z=int(co[0])
    for j in range(dims(fam)):z+=int(co[j+1])*vals[j]
    return int(((z+RAD)%STEP)-RAD)

def build_full(X,cod,fam,co):
    Xi=np.rint(X).astype(np.int64);R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);a=float(cod[0]);b=np.asarray(cod[1:],np.float32)
    for t in range(NT):
        for c in range(C):
            p=0 if t<ah.P else int(np.rint(a+float(np.dot(b,R[c,t-ah.P:t][::-1].astype(np.float32)))))
            d=phase_scalar(fam,co,K,p,c,t);n=int(Xi[c,t])-p;k=(n-d+RAD)//STEP;r=p+d+STEP*k
            if abs(int(Xi[c,t])-r)>RAD:raise RuntimeError(('illegal',fam,c,t))
            K[c,t]=k;R[c,t]=r
    return R,K

def side(fam,co):return bytes([FIDS[fam]])+np.asarray(co,dtype='<i2').tobytes()
def parse_side(bb):
    fam=FAMILIES[bb[0]];n=dims(fam)+1;return fam,np.frombuffer(bb[1:1+2*n],dtype='<i2').copy()
def decode(K,cod,bb):
    fam,co=parse_side(bb);R=np.zeros(K.shape,np.int32);a=float(cod[0]);b=np.asarray(cod[1:],np.float32)
    for t in range(NT):
        for c in range(C):
            p=0 if t<ah.P else int(np.rint(a+float(np.dot(b,R[c,t-ah.P:t][::-1].astype(np.float32)))))
            d=phase_scalar(fam,co,K,p,c,t);R[c,t]=p+d+STEP*int(K[c,t])
    return R

def approx_proxy(N,K0,P0,fam,co):
    Fs=features_arrays(K0,P0)[:dims(fam)];z=np.full(N.shape,int(co[0]),np.int64)
    for j,F in enumerate(Fs):z+=int(co[j+1])*F
    K=np.floor_divide(N-wrap(z)+RAD,STEP).astype(np.int32);return rc.k_proxy(K)

def main(path):
    with h5py.File(path,'r') as hf:
        d=hf['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,C0:C0+C],np.float64).T
    if int(math.floor(eps))!=RAD:raise RuntimeError(('eps',eps))
    _,aco=ah.fits(X);model,cod=cg.model_frame(aco);R0,K0=ah.run_ar(X,cod);P0=R0.astype(np.int64)-STEP*K0.astype(np.int64);N=np.rint(X).astype(np.int64)-P0
    base=rc.k_proxy(K0);rank=[];screens=[]
    for fam in FAMILIES:
        co,hist=fit_law(N,K0,P0,fam);pr=approx_proxy(N,K0,P0,fam,co);sb=side(fam,co);ch=pr+8*len(sb)/(C*NT)
        row={'family':fam,'coefficients':[int(x) for x in co],'approx_proxy_bps':pr,'charged_proxy_bps':ch,'side_bytes':len(sb),'search':hist};screens.append(row);rank.append((ch,fam,co));print(json.dumps({'screen':row}),flush=True)
    rank.sort(key=lambda z:z[0]);recursive=[]
    for _,fam,co in rank[:3]:
        R,K=build_full(X,cod,fam,co);sb=side(fam,co);pr=rc.k_proxy(K);ch=pr+8*len(sb)/(C*NT);me=float(np.max(np.abs(X-R.astype(np.float64))));row={'family':fam,'coefficients':[int(x) for x in co],'recursive_proxy_bps':pr,'charged_proxy_bps':ch,'side_bytes':len(sb),'maxerr':me};recursive.append((ch,fam,co,R,K,sb,row));print(json.dumps({'recursive':row}),flush=True)
    recursive.sort(key=lambda z:z[0]);exact=[];best=('incumbent',INC,None)
    for _,fam,co,R,K,sb,row in recursive[:2]:
        stream,entries,chosen=rc.encode_fixed(K);Kd=cg.decode_components(entries,K.shape)
        if not np.array_equal(Kd,K):raise RuntimeError((fam,'K replay'))
        Rd=decode(Kd,cod,sb)
        if not np.array_equal(Rd,R):raise RuntimeError((fam,'R replay'))
        me=float(np.max(np.abs(X-Rd.astype(np.float64))));total=cg.OUTER_BYTES+len(model)+len(sb)+len(stream)
        if me>eps*(1+5e-6):raise RuntimeError((fam,'hard',me,eps))
        er={'family':fam,'coefficients':[int(x) for x in co],'bytes':int(total),'bps':8*total/(C*NT),'delta_vs_incumbent':int(total-INC),'side_bytes':len(sb),'component_stream_bytes':len(stream),'maxerr':me,'chosen':chosen};exact.append(er);print(json.dumps({'exact':er}),flush=True)
        if total<best[1]:best=(fam,total,er)
    out={'winner':best[0],'bytes':int(best[1]),'incumbent_bytes':INC,'delta_vs_incumbent':int(best[1]-INC),'gain_vs_incumbent':INC/best[1],'matched_sz3_bytes':MATCHED_SZ3,'gain_vs_sz3':MATCHED_SZ3/best[1],'eps':eps,'baseline_proxy_bps':base,'screens':screens,'recursive_candidates':[z[-1] for z in recursive],'exact_candidates':exact,'scope':'Congruential reconstruction-program GCA. A tiny integer formula computes the legal lattice phase from decoder-known previous K, left-current K, predictor residue and optional channel/time coordinates. Coefficients are encoder-searched and physically transmitted in only a few bytes. Top laws are recursively materialized, exact K is arithmetic-coded and independently decoded, and every reconstructed sample is rechecked under the unchanged hard-error bound.'};json.dump(out,open('imperial_gca_congruential_phase_law.json','w'),indent=2);print(json.dumps({'summary':out},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
