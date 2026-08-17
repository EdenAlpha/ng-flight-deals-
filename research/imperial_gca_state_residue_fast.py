import json, math, struct, sys
import h5py
import numpy as np
from numba import njit
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as ah
import imperial_huber_ar32_component_zsm_gps as cg
import imperial_gca_residue_codebook as rc

C=128; NT=30000; C0=512; STEP=267; RAD=133; TRAIN=4096; P=32
INC=2468803; MATCHED_SZ3=2767977
FAMILIES=('prev','prev_left','prev_left_pmod8','prev_prev2_left')
NCTX=(9,81,648,729)

@njit(cache=True)
def clip4n(x):
    if x < -4: x=-4
    elif x > 4: x=4
    return x+4

@njit(cache=True)
def ctxn(fid,K,p,c,t):
    prev=clip4n(K[c,t-1]) if t else 4
    left=clip4n(K[c-1,t]) if c else 4
    if fid==0:return prev
    if fid==1:return prev*9+left
    if fid==2:
        pm=p%STEP
        if pm<0:pm+=STEP
        pb=(pm*8)//STEP
        if pb>7:pb=7
        return (prev*9+left)*8+pb
    prev2=clip4n(K[c,t-2]) if t>1 else 4
    return (prev*9+prev2)*9+left

@njit(cache=True)
def pred32(co,R,c,t):
    if t<P:return 0
    s=np.float32(co[0])
    for j in range(P):
        s=np.float32(s + np.float32(co[j+1])*np.float32(R[c,t-1-j]))
    return int(np.rint(s))

@njit(cache=True)
def build_numba(Xi,co,tab,fid,nt,collect):
    R=np.zeros((C,nt),np.int32);K=np.zeros((C,nt),np.int32)
    if collect:
        ctxs=np.empty(C*nt,np.int32);vals=np.empty(C*nt,np.int64)
    else:
        ctxs=np.empty(1,np.int32);vals=np.empty(1,np.int64)
    q=0
    for t in range(nt):
        for c in range(C):
            p=pred32(co,R,c,t);ci=ctxn(fid,K,p,c,t);d=int(tab[ci]);n0=int(Xi[c,t])-p
            k=(n0-d+RAD)//STEP;r=p+d+STEP*k
            if abs(int(Xi[c,t])-r)>RAD:raise ValueError('illegal')
            K[c,t]=k;R[c,t]=r
            if collect:
                ctxs[q]=ci;vals[q]=n0;q+=1
    return R,K,ctxs,vals

@njit(cache=True)
def decode_numba(K,co,tab,fid):
    R=np.zeros(K.shape,np.int32)
    for t in range(K.shape[1]):
        for c in range(C):
            p=pred32(co,R,c,t);ci=ctxn(fid,K,p,c,t)
            R[c,t]=p+int(tab[ci])+STEP*int(K[c,t])
    return R

def proxy(K):
    return rc.proxy_cost_k(K)/(K.size)

def best_phase(vals,seed=0):
    vals=np.asarray(vals,np.int64)
    if len(vals)>12000:vals=vals[np.linspace(0,len(vals)-1,12000,dtype=np.int64)]
    best=(1e300,int(seed))
    for d in range(-RAD,RAD+1,8):
        s=rc.proxy_cost_k(np.floor_divide(vals-d+RAD,STEP))
        if s<best[0]:best=(s,d)
    c=best[1]
    for d in range(max(-RAD,c-8),min(RAD,c+8)+1):
        s=rc.proxy_cost_k(np.floor_divide(vals-d+RAD,STEP))
        if s<best[0]:best=(s,d)
    return int(best[1])

def refit(ctxs,vals,tab):
    order=np.argsort(ctxs,kind='stable');cs=ctxs[order];vs=vals[order]
    uniq,idx,cnt=np.unique(cs,return_index=True,return_counts=True);out=tab.copy()
    for u,i,n in zip(uniq,idx,cnt):
        if int(n)>=96:out[int(u)]=best_phase(vs[int(i):int(i+n)],int(out[int(u)]))
    return out

def side(fid,tab):return struct.pack('<BH',fid,len(tab))+np.asarray(tab,dtype='<i2').tobytes()
def parse_side(bb):
    fid,n=struct.unpack_from('<BH',bb,0);return fid,np.frombuffer(bb[3:3+2*n],dtype='<i2').copy()

def main(path):
    with h5py.File(path,'r') as hf:
        d=hf['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,C0:C0+C],np.float64).T
    Xi=np.rint(X).astype(np.int64)
    if int(math.floor(eps))!=RAD or np.max(np.abs(X-Xi))>1e-6:raise RuntimeError('source/eps mismatch')
    _,co=ah.fits(X);model,cod=cg.model_frame(co)
    # warm JIT on a legal zero-table prefix
    z=np.zeros(9,np.int16);build_numba(Xi[:,:64],cod,z,0,64,False)
    rows=[];cands=[]
    for fid,fam in enumerate(FAMILIES):
        tab=np.zeros(NCTX[fid],np.int16);hist=[]
        for it in range(2):
            _,K,ctxs,vals=build_numba(Xi,cod,tab,fid,TRAIN,True);pr=proxy(K)
            hist.append({'iter':it,'proxy_bps':pr,'nonzero_phases':int(np.count_nonzero(tab))})
            nt=refit(ctxs,vals,tab)
            if np.array_equal(nt,tab):break
            tab=nt
        R,K,_,_=build_numba(Xi,cod,tab,fid,NT,False);sb=side(fid,tab);pr=proxy(K);charged=pr+8*len(sb)/(C*NT)
        me=float(np.max(np.abs(X-R.astype(np.float64))))
        row={'family':fam,'proxy_bps':pr,'charged_proxy_bps':charged,'side_bytes':len(sb),'nonzero_phases':int(np.count_nonzero(tab)),'maxerr':me,'train':hist}
        rows.append(row);cands.append((charged,fid,fam,tab,R,K,sb));print(json.dumps({'screen':row}),flush=True)
    cands.sort(key=lambda z:z[0]);exact=[];best=('incumbent',INC,None)
    for _,fid,fam,tab,R,K,sb in cands[:2]:
        stream,entries,chosen=rc.encode_fixed(K);Kd=cg.decode_components(entries,K.shape)
        if not np.array_equal(Kd,K):raise RuntimeError((fam,'K replay'))
        fid2,tab2=parse_side(sb);Rd=decode_numba(Kd,cod,tab2,fid2)
        if not np.array_equal(Rd,R):raise RuntimeError((fam,'R replay'))
        me=float(np.max(np.abs(X-Rd.astype(np.float64))));total=cg.OUTER_BYTES+len(model)+len(sb)+len(stream)
        if me>eps*(1+5e-6):raise RuntimeError((fam,'hard',me,eps))
        er={'family':fam,'bytes':int(total),'bps':8*total/(C*NT),'delta_vs_incumbent':int(total-INC),'side_bytes':len(sb),'component_stream_bytes':len(stream),'maxerr':me,'chosen':chosen}
        exact.append(er);print(json.dumps({'exact':er}),flush=True)
        if total<best[1]:best=(fam,total,er)
    out={'winner':best[0],'bytes':int(best[1]),'incumbent_bytes':INC,'delta_vs_incumbent':int(best[1]-INC),'gain_vs_incumbent':INC/best[1],'matched_sz3_bytes':MATCHED_SZ3,'gain_vs_sz3':MATCHED_SZ3/best[1],'eps':eps,'screens':rows,'exact_candidates':exact,'scope':'Compiled fast gate for decoder-state residue-law GCA. Same hard-error legal phase mechanism as PR654; causal reconstruction and decoder replay are compiled, phase tables are charged, and top candidates are physically arithmetic-coded.'}
    json.dump(out,open('imperial_gca_state_residue_fast.json','w'),indent=2);print(json.dumps({'summary':out},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
