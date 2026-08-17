import json, math, struct, sys
import h5py, numpy as np
from numba import njit
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_component_zsm_gps as cg

C=128;NT=30000;C0=512;TRAIN=1024;STEP=267;INC=2468803;SZ3=2767977
CONFIG={'zero':('base',64),'sign':('richall',4),'pref':('richmag',4),'suff':('richmag',4)}

def fit(X):
    # Model: r[c,t] ~= b0 + b1*r[c,t-1] + b2*r[c-1,t].
    # Fit from declared raw-source training prefix; decoder later uses reconstructed state.
    rows=(C-1)*(TRAIN-1);A=np.empty((rows,3),np.float64);y=np.empty(rows,np.float64);q=0
    for t in range(1,TRAIN):
        for c in range(1,C):
            A[q]=(1.0,X[c,t-1],X[c-1,t]);y[q]=X[c,t];q+=1
    co=np.linalg.lstsq(A,y,rcond=None)[0]
    for _ in range(6):
        r=y-A@co;w=np.minimum(1.0,267.0/np.maximum(np.abs(r),1e-12));s=np.sqrt(w);co=np.linalg.lstsq(A*s[:,None],y*s,rcond=None)[0]
    return np.asarray(co,np.float32)

@njit(cache=True)
def run(X,co):
    R=np.zeros((C,NT),np.int32);K=np.zeros((C,NT),np.int32)
    for t in range(NT):
        for c in range(C):
            if t==0 and c==0:p=0
            elif c==0:
                p=int(np.rint(np.float32(co[0])+np.float32(co[1])*np.float32(R[c,t-1])))
            elif t==0:
                p=int(np.rint(np.float32(co[0])+np.float32(co[2])*np.float32(R[c-1,t])))
            else:
                p=int(np.rint(np.float32(co[0])+np.float32(co[1])*np.float32(R[c,t-1])+np.float32(co[2])*np.float32(R[c-1,t])))
            k=int(np.rint((X[c,t]-p)/STEP));K[c,t]=k;R[c,t]=p+STEP*k
    return R,K

@njit(cache=True)
def replay(K,co):
    R=np.zeros(K.shape,np.int32)
    for t in range(K.shape[1]):
        for c in range(K.shape[0]):
            if t==0 and c==0:p=0
            elif c==0:p=int(np.rint(np.float32(co[0])+np.float32(co[1])*np.float32(R[c,t-1])))
            elif t==0:p=int(np.rint(np.float32(co[0])+np.float32(co[2])*np.float32(R[c-1,t])))
            else:p=int(np.rint(np.float32(co[0])+np.float32(co[1])*np.float32(R[c,t-1])+np.float32(co[2])*np.float32(R[c-1,t])))
            R[c,t]=p+STEP*int(K[c,t])
    return R

def encode(K):
    stream=bytearray();entries={};chosen={}
    for comp in cg.COMPONENTS:
        gr,W=CONFIG[comp];bb,nb=cg.encode_component(K,comp,W,NT,gr);sid=cg.config_id(gr,W)
        stream.extend(struct.pack('<BQI',sid,int(nb),len(bb)));stream.extend(bb);entries[comp]=(sid,int(nb),bb);chosen[comp]={'grammar':gr,'W':W,'payload_bytes':len(bb),'bits':int(nb)}
    return bytes(stream),entries,chosen

def h0(K):
    _,n=np.unique(K.reshape(-1),return_counts=True);p=n/n.sum();return float(-(p*np.log2(p)).sum())

def main(path):
    with h5py.File(path,'r') as hf:
        ds=hf['Acoustic'];_,std=m.stats(ds);eps=.1*std;X=np.asarray(ds[:,C0:C0+C],np.float64).T
    if np.max(np.abs(X-np.rint(X)))>1e-6:raise RuntimeError('noninteger source')
    co=fit(X);raw=co.tobytes();cod=np.frombuffer(raw,dtype=np.float32).copy();R,K=run(X,cod);me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('encode hard',me,eps))
    stream,entries,chosen=encode(K);Kd=cg.decode_components(entries,K.shape)
    if not np.array_equal(Kd,K):raise RuntimeError('K replay')
    Rd=replay(Kd,cod)
    if not np.array_equal(Rd,R):raise RuntimeError('R replay')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))));total=34+len(raw)+len(stream)
    out={'generator':'causal_t1_left_current','coefficients':[float(x) for x in co],'model_bytes':len(raw),'K_h0_bps':h0(K),'K_zero_fraction':float(np.mean(K==0)),'component_stream_bytes':len(stream),'bytes':int(total),'bps':8*total/(C*NT),'incumbent_bytes':INC,'delta_vs_incumbent':int(total-INC),'gain_vs_incumbent':INC/total,'matched_sz3_bytes':SZ3,'gain_vs_sz3':SZ3/total,'maxerr':me,'eps':eps,'chosen':chosen,'scope':'Full-hard scale-up of the mini-tile t1+current-left causal generator. Three float32 coefficients are fully charged. Reconstruction is time-major/channel-ascending so current-left state is decoder-known. Step267 K is physically component-coded, exactly decoded, and all 3.84M reconstructed samples are independently replayed under the unchanged hard-error tolerance.'}
    json.dump(out,open('imperial_fullhard_t1_left_generator.json','w'),indent=2);print(json.dumps({'summary':out},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])