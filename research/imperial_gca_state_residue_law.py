import json, math, struct, sys
import h5py
import numpy as np
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as ah
import imperial_huber_ar32_component_zsm_gps as cg
import imperial_gca_residue_codebook as rc

C=128; NT=30000; C0=512; STEP=267; RAD=133; TRAIN=4096
INC=2468803; MATCHED_SZ3=2767977
FAMILIES=('prev','prev_left','prev_left_pmod8','prev_prev2_left')
NCTX={'prev':9,'prev_left':81,'prev_left_pmod8':648,'prev_prev2_left':729}
FAMILY_ID={n:i for i,n in enumerate(FAMILIES)}


def clip4(x):
    return int(max(-4,min(4,int(x))))+4


def ctx_index(fam,K,p,c,t):
    prev=clip4(K[c,t-1]) if t else 4
    left=clip4(K[c-1,t]) if c else 4
    if fam=='prev': return prev
    if fam=='prev_left': return prev*9+left
    if fam=='prev_left_pmod8':
        pb=min(7,(int(p)%STEP)*8//STEP)
        return (prev*9+left)*8+pb
    prev2=clip4(K[c,t-2]) if t>1 else 4
    return (prev*9+prev2)*9+left


def build_state(X,co,table,fam,nt,collect=False):
    Xi=np.rint(X[:,:nt]).astype(np.int64)
    R=np.zeros((C,nt),np.int32);K=np.zeros((C,nt),np.int32)
    a=float(co[0]);b=np.asarray(co[1:],np.float32)
    if collect:
        ctxs=np.empty(C*nt,np.int32); nvals=np.empty(C*nt,np.int64); q=0
    for t in range(nt):
        for c in range(C):
            p=0 if t<ah.P else int(np.rint(a+float(np.dot(b,R[c,t-ah.P:t][::-1].astype(np.float32)))))
            ci=ctx_index(fam,K,p,c,t); d=int(table[ci]); n0=int(Xi[c,t])-p
            k=(n0-d+RAD)//STEP; r=p+d+STEP*k
            if abs(int(Xi[c,t])-r)>RAD: raise RuntimeError(('illegal',fam,c,t,int(Xi[c,t]),p,d,k,r))
            K[c,t]=k;R[c,t]=r
            if collect: ctxs[q]=ci;nvals[q]=n0;q+=1
    if collect:return R,K,ctxs,nvals
    return R,K


def phase_score(vals,d):
    k=np.floor_divide(vals-int(d)+RAD,STEP)
    return rc.proxy_cost_k(k)


def best_phase(vals,seed=0):
    vals=np.asarray(vals,dtype=np.int64)
    if len(vals)>20000: vals=vals[np.linspace(0,len(vals)-1,20000,dtype=np.int64)]
    coarse=list(range(-RAD,RAD+1,8))
    if coarse[-1]!=RAD:coarse.append(RAD)
    best=(1e300,int(seed))
    for d in coarse:
        s=phase_score(vals,d)
        if s<best[0]:best=(s,d)
    center=best[1]
    for d in range(max(-RAD,center-8),min(RAD,center+8)+1):
        s=phase_score(vals,d)
        if s<best[0]:best=(s,d)
    return int(best[1])


def refit_table(ctxs,nvals,old,min_count=64):
    order=np.argsort(ctxs,kind='stable');cs=ctxs[order];vs=nvals[order]
    uniq,idx,cnt=np.unique(cs,return_index=True,return_counts=True)
    tab=np.asarray(old,np.int16).copy()
    for u,i,n in zip(uniq,idx,cnt):
        if int(n)<min_count:continue
        tab[int(u)]=best_phase(vs[int(i):int(i+n)],int(tab[int(u)]))
    return tab


def train_family(X,co,fam):
    tab=np.zeros(NCTX[fam],np.int16);hist=[]
    for it in range(3):
        R,K,ctxs,nvals=build_state(X,co,tab,fam,TRAIN,collect=True)
        pr=rc.proxy_cost_k(K)/(C*TRAIN);hist.append({'iter':it,'proxy_bps':pr,'nonzero_phases':int(np.count_nonzero(tab))})
        nt=refit_table(ctxs,nvals,tab)
        if np.array_equal(nt,tab):break
        tab=nt
    R,K=build_state(X,co,tab,fam,NT,collect=False)
    side=serialize_side(fam,tab)
    pr=rc.k_proxy(K);charged=pr+8*len(side)/(C*NT)
    return tab,R,K,side,pr,charged,hist


def serialize_side(fam,tab):
    return struct.pack('<BH',FAMILY_ID[fam],len(tab))+np.asarray(tab,dtype='<i2').tobytes()


def parse_side(bb):
    fid,n=struct.unpack_from('<BH',bb,0);fam=FAMILIES[fid]
    tab=np.frombuffer(bb[3:3+2*n],dtype='<i2').copy()
    if len(tab)!=NCTX[fam]:raise RuntimeError(('table length',fam,len(tab)))
    return fam,tab


def decode_state(K,co,tab,fam):
    R=np.zeros(K.shape,np.int32);a=float(co[0]);b=np.asarray(co[1:],np.float32)
    for t in range(K.shape[1]):
        for c in range(C):
            p=0 if t<ah.P else int(np.rint(a+float(np.dot(b,R[c,t-ah.P:t][::-1].astype(np.float32)))))
            ci=ctx_index(fam,K,p,c,t);R[c,t]=p+int(tab[ci])+STEP*int(K[c,t])
    return R


def main(path):
    with h5py.File(path,'r') as hf:
        d=hf['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,C0:C0+C],np.float64).T
    if int(math.floor(eps))!=RAD:raise RuntimeError(('eps',eps))
    _,co=ah.fits(X);model,cod=cg.model_frame(co);R0,K0=ah.run_ar(X,cod);baseproxy=rc.k_proxy(K0)
    rows=[];cands=[]
    for fam in FAMILIES:
        tab,R,K,side,pr,charged,hist=train_family(X,cod,fam)
        me=float(np.max(np.abs(X-R.astype(np.float64))))
        row={'family':fam,'proxy_bps':pr,'charged_proxy_bps':charged,'side_bytes':len(side),'nonzero_phases':int(np.count_nonzero(tab)),'maxerr':me,'train':hist}
        rows.append(row);cands.append((charged,fam,tab,R,K,side));print(json.dumps({'screen':row}),flush=True)
    cands.sort(key=lambda z:z[0]);exact=[];best=('incumbent',INC,None)
    for charged,fam,tab,R,K,side in cands[:2]:
        stream,entries,chosen=rc.encode_fixed(K);Kd=cg.decode_components(entries,K.shape)
        if not np.array_equal(Kd,K):raise RuntimeError((fam,'K replay'))
        fam2,tab2=parse_side(side);Rd=decode_state(Kd,cod,tab2,fam2)
        if not np.array_equal(Rd,R):raise RuntimeError((fam,'R replay'))
        me=float(np.max(np.abs(X-Rd.astype(np.float64))));total=cg.OUTER_BYTES+len(model)+len(side)+len(stream)
        if me>eps*(1+5e-6):raise RuntimeError((fam,'hard',me,eps))
        er={'family':fam,'bytes':int(total),'bps':8*total/(C*NT),'delta_vs_incumbent':int(total-INC),'side_bytes':len(side),'component_stream_bytes':len(stream),'maxerr':me,'chosen':chosen}
        exact.append(er);print(json.dumps({'exact':er}),flush=True)
        if total<best[1]:best=(fam,total,er)
    out={'winner':best[0],'bytes':int(best[1]),'incumbent_bytes':INC,'delta_vs_incumbent':int(best[1]-INC),'gain_vs_incumbent':INC/best[1],'matched_sz3_bytes':MATCHED_SZ3,'gain_vs_sz3':MATCHED_SZ3/best[1],'eps':eps,'baseline_proxy_bps':baseproxy,'screens':rows,'exact_candidates':exact,'scope':'Decoder-state residue-law GCA. A tiny transmitted phase table maps decoder-known K/history and optionally predictor residue state to one of the 267 legal lattice phases at every sample. The phase choice is therefore regenerated rather than transmitted sample-by-sample. Tables are learned only by encoder search, fully charged as side information, then the resulting full AR32 K field is physically arithmetic-coded. Decoder parses exact K, regenerates every phase from already decoded state, replays all 3.84M samples and verifies the unchanged hard error.'}
    json.dump(out,open('imperial_gca_state_residue_law.json','w'),indent=2);print(json.dumps({'summary':out},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
