import json, math, struct, sys
import h5py
import numpy as np
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as ah
import imperial_huber_ar32_component_zsm_gps as cg
import imperial_gca_residue_codebook as rc
import imperial_gca_state_residue_law as sl

C=128; NT=30000; C0=512; STEP=267; RAD=133
INC=2468803; MATCHED_SZ3=2767977
# Public automaton menu. State is per channel and persists through time.
SPECS=[(16,3,0),(16,5,3),(32,3,0),(32,5,3),(64,3,0),(64,5,3),(128,3,0),(128,5,3)]


def pbin(p):
    return ((int(p)%STEP)*4)//STEP


def next_state(s,k,p,S,a,b):
    return (a*int(s)+sl.clip4(k)+b*pbin(p))%S


def approx_pass(N,P,Kseed,table,S,a,b,collect=False):
    st=np.zeros(C,np.int32); K=np.zeros_like(Kseed,dtype=np.int32)
    if collect:
        states=np.empty(C*NT,np.int32); vals=np.empty(C*NT,np.int64);q=0
    for t in range(NT):
        for c in range(C):
            s=int(st[c]);d=int(table[s]);n=int(N[c,t]);k=(n-d+RAD)//STEP
            K[c,t]=k
            if collect:states[q]=s;vals[q]=n;q+=1
            st[c]=next_state(s,k,P[c,t],S,a,b)
    return (K,states,vals) if collect else K


def train_approx(N,P,K0,S,a,b):
    tab=np.zeros(S,np.int16);hist=[]
    for it in range(3):
        K,states,vals=approx_pass(N,P,K0,tab,S,a,b,True)
        pr=rc.k_proxy(K);hist.append({'iter':it,'proxy_bps':pr,'nonzero_phases':int(np.count_nonzero(tab))})
        nt=sl.refit_table(states,vals,tab,min_count=128)
        if np.array_equal(nt,tab):break
        tab=nt
    K=approx_pass(N,P,K0,tab,S,a,b,False)
    return tab,rc.k_proxy(K),hist


def build_full(X,co,tab,S,a,b):
    Xi=np.rint(X).astype(np.int64);R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);st=np.zeros(C,np.int32)
    aa=float(co[0]);bb=np.asarray(co[1:],np.float32)
    for t in range(NT):
        for c in range(C):
            p=0 if t<ah.P else int(np.rint(aa+float(np.dot(bb,R[c,t-ah.P:t][::-1].astype(np.float32)))))
            s=int(st[c]);d=int(tab[s]);n=int(Xi[c,t])-p;k=(n-d+RAD)//STEP;r=p+d+STEP*k
            if abs(int(Xi[c,t])-r)>RAD:raise RuntimeError(('illegal',c,t))
            K[c,t]=k;R[c,t]=r;st[c]=next_state(s,k,p,S,a,b)
    return R,K


def side(spec_id,tab):
    return bytes([spec_id])+np.asarray(tab,dtype='<i2').tobytes()


def parse_side(bb):
    i=bb[0];S,a,b=SPECS[i];tab=np.frombuffer(bb[1:1+2*S],dtype='<i2').copy();return i,S,a,b,tab


def decode(K,co,bb):
    _,S,a,b,tab=parse_side(bb);R=np.zeros(K.shape,np.int32);st=np.zeros(C,np.int32);aa=float(co[0]);cc=np.asarray(co[1:],np.float32)
    for t in range(NT):
        for c in range(C):
            p=0 if t<ah.P else int(np.rint(aa+float(np.dot(cc,R[c,t-ah.P:t][::-1].astype(np.float32)))))
            s=int(st[c]);R[c,t]=p+int(tab[s])+STEP*int(K[c,t]);st[c]=next_state(s,int(K[c,t]),p,S,a,b)
    return R


def main(path):
    with h5py.File(path,'r') as hf:
        d=hf['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,C0:C0+C],np.float64).T
    if int(math.floor(eps))!=RAD:raise RuntimeError(('eps',eps))
    _,co=ah.fits(X);model,cod=cg.model_frame(co);R0,K0=ah.run_ar(X,cod)
    P0=R0.astype(np.int64)-STEP*K0.astype(np.int64);N=np.rint(X).astype(np.int64)-P0
    base=rc.k_proxy(K0);screens=[];rank=[]
    for i,(S,a,b) in enumerate(SPECS):
        tab,pr,hist=train_approx(N,P0,K0,S,a,b);sb=side(i,tab);charged=pr+8*len(sb)/(C*NT)
        row={'spec_id':i,'states':S,'a':a,'p_weight':b,'approx_proxy_bps':pr,'charged_proxy_bps':charged,'side_bytes':len(sb),'nonzero_phases':int(np.count_nonzero(tab)),'train':hist}
        screens.append(row);rank.append((charged,i,tab));print(json.dumps({'screen':row}),flush=True)
    rank.sort(key=lambda z:z[0]);full=[]
    for _,i,tab in rank[:4]:
        S,a,b=SPECS[i];R,K=build_full(X,cod,tab,S,a,b);sb=side(i,tab);pr=rc.k_proxy(K);charged=pr+8*len(sb)/(C*NT);me=float(np.max(np.abs(X-R.astype(np.float64))))
        row={'spec_id':i,'states':S,'a':a,'p_weight':b,'recursive_proxy_bps':pr,'charged_proxy_bps':charged,'side_bytes':len(sb),'maxerr':me}
        full.append((charged,i,tab,R,K,sb,row));print(json.dumps({'recursive':row}),flush=True)
    full.sort(key=lambda z:z[0]);exact=[];best=('incumbent',INC,None)
    for _,i,tab,R,K,sb,row in full[:2]:
        stream,entries,chosen=rc.encode_fixed(K);Kd=cg.decode_components(entries,K.shape)
        if not np.array_equal(Kd,K):raise RuntimeError((i,'K replay'))
        Rd=decode(Kd,cod,sb)
        if not np.array_equal(Rd,R):raise RuntimeError((i,'R replay'))
        me=float(np.max(np.abs(X-Rd.astype(np.float64))));total=cg.OUTER_BYTES+len(model)+len(sb)+len(stream)
        if me>eps*(1+5e-6):raise RuntimeError((i,'hard',me,eps))
        er={'spec_id':i,'states':SPECS[i][0],'a':SPECS[i][1],'p_weight':SPECS[i][2],'bytes':int(total),'bps':8*total/(C*NT),'delta_vs_incumbent':int(total-INC),'side_bytes':len(sb),'component_stream_bytes':len(stream),'maxerr':me,'chosen':chosen}
        exact.append(er);print(json.dumps({'exact':er}),flush=True)
        if total<best[1]:best=(f'automaton_{i}',total,er)
    out={'winner':best[0],'bytes':int(best[1]),'incumbent_bytes':INC,'delta_vs_incumbent':int(best[1]-INC),'gain_vs_incumbent':INC/best[1],'matched_sz3_bytes':MATCHED_SZ3,'gain_vs_sz3':MATCHED_SZ3/best[1],'eps':eps,'baseline_proxy_bps':base,'screens':screens,'recursive_candidates':[z[-1] for z in full],'exact_candidates':exact,'scope':'Finite-state reconstruction-program GCA. A tiny public automaton carries decoder state independently along each channel. Each state selects one of 267 legal lattice phases; already-decoded K and predictor residue update the state. Only a menu selector and one int16 phase per state are transmitted, so a few hundred bytes generate millions of legal reconstruction choices. Encoder-only training uses the baseline predictor for screening, then top candidates are recursively materialized. Final candidates physically arithmetic-code exact K, independently decode the automaton reconstruction, and enforce the unchanged hard-error bound.'}
    json.dump(out,open('imperial_gca_phase_automaton.json','w'),indent=2);print(json.dumps({'summary':out},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
