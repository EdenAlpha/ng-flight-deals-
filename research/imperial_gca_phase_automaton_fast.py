import json, math, sys
import h5py
import numpy as np
from numba import njit
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as ah
import imperial_huber_ar32_component_zsm_gps as cg
import imperial_gca_residue_codebook as rc
import imperial_gca_state_residue_law as sl

C=128;NT=30000;C0=512;STEP=267;RAD=133;P=32;TRAIN=8192
INC=2468803;MATCHED_SZ3=2767977
SPECS=((16,3,0),(16,5,3),(32,3,0),(32,5,3),(64,3,0),(64,5,3),(128,3,0),(128,5,3))

@njit(cache=True)
def pbin(p):
    x=p%STEP
    if x<0:x+=STEP
    return (x*4)//STEP

@njit(cache=True)
def clip4n(x):
    if x<-4:x=-4
    elif x>4:x=4
    return x+4

@njit(cache=True)
def proxy_sum(K):
    s=0.0
    for i in range(K.shape[0]):
        for j in range(K.shape[1]):
            a=abs(int(K[i,j]));s+=1.0
            if a:
                q=0;v=a
                while v>1:q+=1;v//=2
                s+=2.0+2.0*q
    return s

@njit(cache=True)
def approx_numba(N,P0,tab,S,a,b,nt,collect):
    st=np.zeros(C,np.int32);K=np.zeros((C,nt),np.int32)
    if collect:
        states=np.empty(C*nt,np.int32);vals=np.empty(C*nt,np.int64)
    else:
        states=np.empty(1,np.int32);vals=np.empty(1,np.int64)
    q=0
    for t in range(nt):
        for c in range(C):
            s=int(st[c]);d=int(tab[s]);n=int(N[c,t]);k=(n-d+RAD)//STEP;K[c,t]=k
            if collect:states[q]=s;vals[q]=n;q+=1
            st[c]=(a*s+clip4n(k)+b*pbin(int(P0[c,t])))%S
    return K,states,vals

@njit(cache=True)
def pred32(co,R,c,t):
    if t<P:return 0
    s=np.float32(co[0])
    for j in range(P):s=np.float32(s+np.float32(co[j+1])*np.float32(R[c,t-1-j]))
    return int(np.rint(s))

@njit(cache=True)
def full_numba(Xi,co,tab,S,a,b):
    R=np.zeros((C,NT),np.int32);K=np.zeros((C,NT),np.int32);st=np.zeros(C,np.int32)
    for t in range(NT):
        for c in range(C):
            p=pred32(co,R,c,t);s=int(st[c]);d=int(tab[s]);n=int(Xi[c,t])-p;k=(n-d+RAD)//STEP;r=p+d+STEP*k
            if abs(int(Xi[c,t])-r)>RAD:raise ValueError('illegal')
            K[c,t]=k;R[c,t]=r;st[c]=(a*s+clip4n(k)+b*pbin(p))%S
    return R,K

@njit(cache=True)
def decode_numba(K,co,tab,S,a,b):
    R=np.zeros(K.shape,np.int32);st=np.zeros(C,np.int32)
    for t in range(K.shape[1]):
        for c in range(C):
            p=pred32(co,R,c,t);s=int(st[c]);R[c,t]=p+int(tab[s])+STEP*int(K[c,t]);st[c]=(a*s+clip4n(int(K[c,t]))+b*pbin(p))%S
    return R

def best_phase(vals,seed=0):
    vals=np.asarray(vals,np.int64)
    if len(vals)>16000:vals=vals[np.linspace(0,len(vals)-1,16000,dtype=np.int64)]
    best=(1e300,int(seed))
    for d in range(-RAD,RAD+1,8):
        k=np.floor_divide(vals-d+RAD,STEP);sc=rc.proxy_cost_k(k)
        if sc<best[0]:best=(sc,d)
    c=best[1]
    for d in range(max(-RAD,c-8),min(RAD,c+8)+1):
        k=np.floor_divide(vals-d+RAD,STEP);sc=rc.proxy_cost_k(k)
        if sc<best[0]:best=(sc,d)
    return int(best[1])

def refit(states,vals,tab):
    order=np.argsort(states,kind='stable');ss=states[order];vv=vals[order]
    uniq,idx,cnt=np.unique(ss,return_index=True,return_counts=True);out=tab.copy()
    for u,i,n in zip(uniq,idx,cnt):
        if int(n)>=128:out[int(u)]=best_phase(vv[int(i):int(i+n)],int(out[int(u)]))
    return out

def proxy(K):return float(proxy_sum(K)/K.size)
def side(i,tab):return bytes([i])+np.asarray(tab,dtype='<i2').tobytes()
def parse_side(bb):
    i=bb[0];S,a,b=SPECS[i];tab=np.frombuffer(bb[1:1+2*S],dtype='<i2').copy();return i,S,a,b,tab

def main(path):
    with h5py.File(path,'r') as hf:
        d=hf['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,C0:C0+C],np.float64).T
    Xi=np.rint(X).astype(np.int64)
    if int(math.floor(eps))!=RAD or np.max(np.abs(X-Xi))>1e-6:raise RuntimeError('source/eps')
    _,co=ah.fits(X);model,cod=cg.model_frame(co);R0,K0=ah.run_ar(X,cod);P0=R0.astype(np.int64)-STEP*K0.astype(np.int64);N=Xi-P0
    # compile kernels
    approx_numba(N[:,:64],P0[:,:64],np.zeros(16,np.int16),16,3,0,64,False)
    screens=[];rank=[]
    for i,(S,a,b) in enumerate(SPECS):
        tab=np.zeros(S,np.int16);hist=[]
        for it in range(2):
            K,states,vals=approx_numba(N,P0,tab,S,a,b,TRAIN,True);pr=proxy(K);hist.append({'iter':it,'proxy_bps':pr,'nonzero_phases':int(np.count_nonzero(tab))})
            nt=refit(states,vals,tab)
            if np.array_equal(nt,tab):break
            tab=nt
        K,_,_=approx_numba(N,P0,tab,S,a,b,NT,False);pr=proxy(K);sb=side(i,tab);charged=pr+8*len(sb)/(C*NT)
        row={'spec_id':i,'states':S,'a':a,'p_weight':b,'approx_proxy_bps':pr,'charged_proxy_bps':charged,'side_bytes':len(sb),'nonzero_phases':int(np.count_nonzero(tab)),'train':hist}
        screens.append(row);rank.append((charged,i,tab));print(json.dumps({'screen':row}),flush=True)
    rank.sort(key=lambda z:z[0]);full=[]
    for _,i,tab in rank[:4]:
        S,a,b=SPECS[i];R,K=full_numba(Xi,cod,tab,S,a,b);sb=side(i,tab);pr=proxy(K);charged=pr+8*len(sb)/(C*NT);me=float(np.max(np.abs(X-R.astype(np.float64))))
        row={'spec_id':i,'states':S,'a':a,'p_weight':b,'recursive_proxy_bps':pr,'charged_proxy_bps':charged,'side_bytes':len(sb),'maxerr':me}
        full.append((charged,i,tab,R,K,sb,row));print(json.dumps({'recursive':row}),flush=True)
    full.sort(key=lambda z:z[0]);exact=[];best=('incumbent',INC,None)
    for _,i,tab,R,K,sb,row in full[:2]:
        stream,entries,chosen=rc.encode_fixed(K);Kd=cg.decode_components(entries,K.shape)
        if not np.array_equal(Kd,K):raise RuntimeError((i,'K replay'))
        _,S,a,b,tab2=parse_side(sb);Rd=decode_numba(Kd,cod,tab2,S,a,b)
        if not np.array_equal(Rd,R):raise RuntimeError((i,'R replay'))
        me=float(np.max(np.abs(X-Rd.astype(np.float64))));total=cg.OUTER_BYTES+len(model)+len(sb)+len(stream)
        if me>eps*(1+5e-6):raise RuntimeError((i,'hard',me,eps))
        er={'spec_id':i,'states':S,'a':a,'p_weight':b,'bytes':int(total),'bps':8*total/(C*NT),'delta_vs_incumbent':int(total-INC),'side_bytes':len(sb),'component_stream_bytes':len(stream),'maxerr':me,'chosen':chosen}
        exact.append(er);print(json.dumps({'exact':er}),flush=True)
        if total<best[1]:best=(f'automaton_{i}',total,er)
    out={'winner':best[0],'bytes':int(best[1]),'incumbent_bytes':INC,'delta_vs_incumbent':int(best[1]-INC),'gain_vs_incumbent':INC/best[1],'matched_sz3_bytes':MATCHED_SZ3,'gain_vs_sz3':MATCHED_SZ3/best[1],'eps':eps,'screens':screens,'recursive_candidates':[z[-1] for z in full],'exact_candidates':exact,'scope':'Compiled finite-state reconstruction-program GCA gate. Phase tables are learned on a public prefix, recursively materialized on all 3.84M samples, physically charged, exact K is arithmetic-coded, and decoder replay enforces unchanged hard error.'}
    json.dump(out,open('imperial_gca_phase_automaton_fast.json','w'),indent=2);print(json.dumps({'summary':out},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
