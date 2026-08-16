import json,sys
import h5py,numpy as np
import imperial_dyadic_shared_resonator as ar
import imperial_decoder_phase_automaton as m
import imperial_persistent_ar32_full_array_jit as aj
import imperial_ar32_conditional_bitplane_rank as c

C0=512; C=128; T=30000; TRAIN=1024; P=32; STEP=267; CHARGE=32
PARTS=((128,30000),(8,1024),(128,4096))
c.C=C; c.T=T; c.DEPTHS=(2,); c.h.PARTS=PARTS
aj.m.P=32; aj.m.m.STEP=STEP

def zstd_candidate(B):
    raw=np.packbits(B.ravel(),bitorder='little').tobytes(); z=m.Z.compress(raw)
    body=c.h.uvar(len(z))+z
    return (1+len(c.h.uvar(len(body)))+len(body),0,body,'zstd',None)

def enum_candidate(B,pid):
    cb,tb=PARTS[pid-1]; body,_=c.h.enum_partition_encode(B,cb,tb)
    return (1+len(c.h.uvar(len(body)))+len(body),pid,body,'enum',[cb,tb])

def cond_candidate(B,U,b):
    body=c.cenc(B,U,b,2)
    return (1+len(c.h.uvar(len(body)))+len(body),64,body,'conditional',2)

def frozen_choices(B,U,b):
    rows=[zstd_candidate(B)]
    # Frozen from the successful 128x4096 screen: no target-specific grammar search here.
    if b>=8 or b==1: rows.append(enum_candidate(B,1))
    elif b in (7,6): rows.append(enum_candidate(B,2))
    elif b in (3,2):
        rows.append(enum_candidate(B,1)); rows.append(cond_candidate(B,U,b))
    return sorted(rows)

def encode(K):
    U=m.zig(K); nb=max(1,int(U.max()).bit_length()); raw=bytearray(c.MAGIC)+c.h.uvar(C)+c.h.uvar(T)+c.h.uvar(nb); info=[]
    for b in range(nb-1,-1,-1):
        B=((U>>b)&1).astype(np.uint8); rows=frozen_choices(B,U,b); size,tag,body,kind,detail=rows[0]
        raw.append(tag); raw+=c.h.uvar(len(body)); raw+=body
        info.append({'bit':b,'mode':kind,'detail':detail,'frame_bytes':size,'candidates':[{'mode':r[3],'detail':r[4],'bytes':r[0]} for r in rows]})
    raw=bytes(raw); z=m.Z.compress(raw)
    if len(z)<len(raw): return b'\x01'+z,'zstd',info,len(raw)
    return b'\x00'+raw,'raw',info,len(raw)

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic']; _,sd=m.stats(d); eps=.1*sd; X=np.asarray(d[:,C0:C0+C],np.float64).T
    co=ar.fit_shared(X[:,:TRAIN],P); mb,cd=ar.model_frame(co); R,K=aj.build(X,cd)
    fr=m.encode_k(K); base=int(mb)+int(fr[0])+CHARGE
    K0=np.asarray(fr[2],np.int32); R0=aj.decode(K0,cd)
    if not np.array_equal(R0,R): raise RuntimeError('baseline replay')
    e0=float(np.max(np.abs(X-R0.astype(np.float64))))
    if e0>eps*(1+5e-6): raise RuntimeError(('baseline hard',e0,eps))
    sz,ori=m.szrun(X,eps)
    buf,outer,planes,rawlen=encode(K); KD=c.decode(buf)
    if not np.array_equal(KD,K): raise RuntimeError('conditional K mismatch')
    RD=aj.decode(KD,cd)
    if not np.array_equal(RD,R): raise RuntimeError('conditional AR replay')
    err=float(np.max(np.abs(X-RD.astype(np.float64))))
    if err>eps*(1+5e-6): raise RuntimeError(('conditional hard',err,eps))
    total=int(mb)+len(buf)+CHARGE
    out={'shape':[C,T],'c0':C0,'global_std':sd,'eps':eps,'conditional_bytes':total,'address_bytes':len(buf),'address_raw_bytes':rawlen,'outer':outer,'ar32_bytes':base,'ar32_innovation_bytes':int(fr[0]),'ar32_rep':fr[1],'sz3_bytes':int(sz),'sz3_orientation':ori,'gain_vs_ar32':base/total,'gain_vs_sz3':sz/total,'maxerr':err,'model_bytes':int(mb),'planes':planes,'scope':'Full 128x30000 hard-block validation using a frozen address grammar selected before this run from the successful 128x4096 scale gate. AR32 reconstruction, epsilon and exact replay contract are unchanged. Bitplane modes are frozen by bit position: high/bit1 global finite rank; bits7/6 8x1024 finite rank; bits3/2 compete global finite rank versus depth-2 decoder-known higher-prefix rank; bits5/4/0 stay incumbent Zstd. Within each frozen allowed set, a one-byte selector chooses the smaller actual serialized frame. No new address family or context depth is searched on this full target. Exact K decode, exact AR32 replay and source hard error are mandatory; matched SZ3 and whole-block AR32 encode_k are rerun on the identical 128x30000 object.'}
    print(json.dumps(out,indent=2)); json.dump(out,open('imperial_ar32_conditional_rank_full_hard.json','w'),indent=2)
if __name__=='__main__': main(sys.argv[1])
