import json, math, sys
import h5py
import numpy as np
import zstandard as zstd
from numba import njit
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as ah
import imperial_huber_ar32_component_zsm_gps as cg

C=128;NT=30000;C0=512;P=32;RAD=133
INC=2468803;MATCHED_SZ3=2767977;HEADER=64
# policy: 0 clamp, 1 source-center, 2/3/4 interior margins, 5 one-step future target
POLICIES=((0,0),(1,0),(2,64),(2,133),(2,200),(5,0))

@njit(cache=True)
def pred(co,R,c,t):
    if t<P:return 0
    s=np.float32(co[0])
    for j in range(P):s=np.float32(s+np.float32(co[j+1])*np.float32(R[c,t-1-j]))
    return int(np.rint(s))

@njit(cache=True)
def choose_r(Xi,co,R,c,t,p,kind,arg):
    x=int(Xi[c,t]);lo=x-RAD;hi=x+RAD
    if kind==0:
        return lo if p<lo else hi
    if kind==1:return x
    if kind==2:
        mm=arg
        if mm<0:mm=0
        if mm>2*RAD:mm=2*RAD
        return lo+mm if p<lo else hi-mm
    # one-step target: choose current legal r that makes next predictor
    # as close as possible to the center of next source hard interval.
    if t+1>=NT:return lo if p<lo else hi
    b0=float(co[1])
    if abs(b0)<1e-9:return lo if p<lo else hi
    const=float(co[0])
    for j in range(1,P):
        idx=t-j
        if idx>=0:const += float(co[j+1])*float(R[c,idx])
    rr=int(np.rint((float(Xi[c,t+1])-const)/b0))
    if rr<lo:rr=lo
    elif rr>hi:rr=hi
    return rr

@njit(cache=True)
def encode_policy(Xi,co,kind,arg):
    R=np.zeros((C,NT),np.int32);J=np.zeros((C,NT),np.int32)
    events=0
    for c in range(C):
        for t in range(NT):
            p=pred(co,R,c,t);x=int(Xi[c,t]);lo=x-RAD;hi=x+RAD
            if p>=lo and p<=hi:r=p
            else:
                r=choose_r(Xi,co,R,c,t,p,kind,arg);events+=1
            R[c,t]=r;J[c,t]=r-p
    return R,J,events

@njit(cache=True)
def decode_j(J,co):
    R=np.zeros(J.shape,np.int32)
    for c in range(C):
        for t in range(NT):
            p=pred(co,R,c,t);R[c,t]=p+int(J[c,t])
    return R

def zc(raw):return zstd.ZstdCompressor(level=19).compress(raw)
def zd(raw):return zstd.ZstdDecompressor().decompress(raw)

def pack_j(J):
    flat=np.asarray(J,np.int32).reshape(-1);mask=(flat!=0);mb=np.packbits(mask.astype(np.uint8),bitorder='little').tobytes();mzc=zc(mb)
    nz=flat[mask]
    reps=[]
    if len(nz)==0:reps.append((0,b'',np.dtype('<i2')))
    else:
        if int(nz.min())>=-32768 and int(nz.max())<=32767:
            reps.append((0,zc(np.asarray(nz,dtype='<i2').tobytes()),np.dtype('<i2')))
        reps.append((1,zc(np.asarray(nz,dtype='<i4').tobytes()),np.dtype('<i4')))
        d=np.diff(np.concatenate((np.array([0],np.int64),nz.astype(np.int64))))
        if int(d.min())>=-2147483648 and int(d.max())<=2147483647:
            reps.append((2,zc(np.asarray(d,dtype='<i4').tobytes()),np.dtype('<i4')))
    codec,cbytes,dtype=min(reps,key=lambda x:len(x[1]))
    return mzc,cbytes,codec,int(mask.sum()),len(mb)

def unpack_j(mzc,cbytes,codec,nevents,n):
    mb=zd(mzc);mask=np.unpackbits(np.frombuffer(mb,np.uint8),bitorder='little')[:n].astype(bool)
    if int(mask.sum())!=nevents:raise RuntimeError('mask count')
    if nevents==0:nz=np.empty(0,np.int32)
    elif codec==0:nz=np.frombuffer(zd(cbytes),dtype='<i2').astype(np.int32)
    elif codec==1:nz=np.frombuffer(zd(cbytes),dtype='<i4').astype(np.int32)
    elif codec==2:nz=np.cumsum(np.frombuffer(zd(cbytes),dtype='<i4').astype(np.int64)).astype(np.int32)
    else:raise RuntimeError('codec')
    if len(nz)!=nevents:raise RuntimeError(('corr count',len(nz),nevents))
    flat=np.zeros(n,np.int32);flat[mask]=nz;return flat.reshape(C,NT)

def h0(a):
    _,cnt=np.unique(np.asarray(a).reshape(-1),return_counts=True);p=cnt/cnt.sum();return float(-(p*np.log2(p)).sum())

def main(path):
    with h5py.File(path,'r') as hf:
        d=hf['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,C0:C0+C],np.float64).T
    Xi=np.rint(X).astype(np.int64)
    if int(math.floor(eps))!=RAD or np.max(np.abs(X-Xi))>1e-6:raise RuntimeError(('source/eps',eps))
    _,co=ah.fits(X);model,cod=cg.model_frame(co)
    # warm JIT
    tiny=np.zeros((C,NT),np.int64); # actual call below compiles once
    rows=[];cands=[]
    for pid,(kind,arg) in enumerate(POLICIES):
        R,J,ev=encode_policy(Xi,cod,kind,arg);me=float(np.max(np.abs(X-R.astype(np.float64))))
        if me>eps*(1+5e-6):raise RuntimeError((pid,'hard',me,eps))
        mzc,cb,cc,nev,maskraw=pack_j(J);total=HEADER+len(model)+len(mzc)+len(cb)
        row={'policy_id':pid,'kind':kind,'arg':arg,'events':int(ev),'event_fraction':float(ev/(C*NT)),'zero_fraction':float(1-ev/(C*NT)),'correction_h0_bps_all_samples':h0(J),'mask_zstd_bytes':len(mzc),'correction_zstd_bytes':len(cb),'correction_codec':cc,'bytes':int(total),'bps':8*total/(C*NT),'delta_vs_incumbent':int(total-INC),'maxerr':me}
        rows.append(row);cands.append((total,pid,R,J,mzc,cb,cc,nev,row));print(json.dumps({'candidate':row}),flush=True)
    cands.sort(key=lambda z:z[0]);total,pid,R,J,mzc,cb,cc,nev,brow=cands[0]
    Jd=unpack_j(mzc,cb,cc,nev,C*NT);Rd=decode_j(Jd,cod)
    if not np.array_equal(Jd,J):raise RuntimeError('J replay')
    if not np.array_equal(Rd,R):raise RuntimeError('R replay')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('decode hard',me,eps))
    out={'winner_policy':int(pid),'bytes':int(total),'bps':8*total/(C*NT),'incumbent_bytes':INC,'delta_vs_incumbent':int(total-INC),'gain_vs_incumbent':INC/total,'matched_sz3_bytes':MATCHED_SZ3,'gain_vs_sz3':MATCHED_SZ3/total,'two_x_target_bytes':MATCHED_SZ3/2.0,'bytes_above_2x_target':total-MATCHED_SZ3/2.0,'eps':eps,'maxerr':me,'model_bytes':len(model),'header_bytes':HEADER,'candidates':rows,'scope':'Sparse legal-intervention GCA codec. Decoder free-runs the shared serialized Huber AR32 predictor whenever its prediction is already within the source hard-error interval. Encoder emits an exact integer intervention only when needed and chooses the legal reconstruction by a fixed public controller, including a noncausal one-step future-target policy. Event mask and exact corrections are physically zstd-compressed, framing/model bytes are charged, then decoder independently recovers J and replays every sample under the unchanged hard error.'}
    json.dump(out,open('imperial_gca_sparse_intervention.json','w'),indent=2);print(json.dumps({'summary':out},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
