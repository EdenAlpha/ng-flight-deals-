import json,sys
import h5py,numpy as np
import imperial_dyadic_shared_resonator as ar
import imperial_decoder_phase_automaton as m
import imperial_persistent_ar32_full_array_jit as aj
import imperial_ar32_hybrid_bitplane_rank as h
import imperial_ar32_hybrid_bitplane_rank_v2  # patches h.decode_hybrid parser only

T0=14488; C0=512; C=32; T=4096; TRAIN=1024; P=32; STEP=267; CHARGE=32
DEPTHS=(1,2,3,4,99); MAGIC=b'CBR1'
aj.m.P=32; aj.m.m.STEP=STEP

def keys(U,b,d):
    x=(U>>(b+1)).ravel()
    if d==99:return x
    return x & np.uint64((1<<d)-1)

def cenc(B,U,b,d):
    k=keys(U,b,d); out=bytearray()
    for z in np.unique(k):
        ix=np.flatnonzero(k==z); q=B.ravel()[ix]; one=int(q.sum()); p=h.binom_rank_encode(q)
        out+=h.uvar(one)+h.uvar(len(p))+p
    return bytes(out)

def cdec(raw,pos,U,b,d):
    k=keys(U,b,d); q=np.empty(k.size,np.uint8)
    for z in np.unique(k):
        ix=np.flatnonzero(k==z); one,pos=h.read_uvar(raw,pos); n,pos=h.read_uvar(raw,pos)
        q[ix]=h.binom_rank_decode(raw[pos:pos+n],len(ix),one); pos+=n
    return q.reshape(U.shape),pos

def choices(B,U,b):
    base=h.plane_candidates(B,h.PARTS); z=next(x for x in base if x['mode']=='zstd'); e=min((x for x in base if x['mode']=='enum'),key=lambda x:x['frame_bytes'])
    rows=[(z['frame_bytes'],0,z['body'],'zstd',None),(e['frame_bytes'],e['mode_id'],e['body'],'enum',e['partition'])]
    for i,d in enumerate(DEPTHS):
        body=cenc(B,U,b,d); rows.append((1+len(h.uvar(len(body)))+len(body),64+i,body,'conditional',d))
    return sorted(rows)

def encode(K):
    U=m.zig(K); nb=max(1,int(U.max()).bit_length()); raw=bytearray(MAGIC)+h.uvar(C)+h.uvar(T)+h.uvar(nb); info=[]
    for b in range(nb-1,-1,-1):
        B=((U>>b)&1).astype(np.uint8); r=choices(B,U,b); size,tag,body,kind,detail=r[0]
        raw.append(tag); raw+=h.uvar(len(body)); raw+=body
        info.append({'bit':b,'mode':kind,'detail':detail,'bytes':size,'zstd':next(x[0] for x in r if x[3]=='zstd'),'enum':next(x[0] for x in r if x[3]=='enum'),'best_cond':min(x[0] for x in r if x[3]=='conditional')})
    raw=bytes(raw); z=m.Z.compress(raw)
    if len(z)<len(raw):return b'\x01'+z,'zstd',info
    return b'\x00'+raw,'raw',info

def decode(buf):
    raw=m.D.decompress(buf[1:]) if buf[0] else bytes(buf[1:])
    if raw[:4]!=MAGIC:raise RuntimeError('magic')
    pos=4; cc,pos=h.read_uvar(raw,pos); tt,pos=h.read_uvar(raw,pos); nb,pos=h.read_uvar(raw,pos); U=np.zeros((cc,tt),np.uint64)
    for b in range(nb-1,-1,-1):
        tag=raw[pos]; pos+=1; n,pos=h.read_uvar(raw,pos); end=pos+n
        if tag==0:
            q,p=h.read_uvar(raw,pos); bb=m.D.decompress(raw[p:p+q]); B=np.unpackbits(np.frombuffer(bb,np.uint8),bitorder='little')[:cc*tt].reshape(cc,tt); p+=q
        elif 1<=tag<=len(h.PARTS):
            B,p=h.enum_partition_decode(raw,pos,(cc,tt),*h.PARTS[tag-1])
        elif 64<=tag<64+len(DEPTHS):
            B,p=cdec(raw,pos,U,b,DEPTHS[tag-64])
        else:raise RuntimeError(('tag',tag,b))
        if p!=end:raise RuntimeError(('frame',b,p,end))
        pos=end
        U|=B.astype(np.uint64)<<b
    if pos!=len(raw):raise RuntimeError(('trailing',pos,len(raw)))
    return m.unzig(U).reshape(cc,tt)

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic']; _,sd=m.stats(d); eps=.1*sd; X=np.asarray(d[T0:T0+T,C0:C0+C],np.float64).T
    co=ar.fit_shared(X[:,:TRAIN],P); mb,cd=ar.model_frame(co); R,K=aj.build(X,cd); fr=m.encode_k(K)
    base=int(mb)+int(fr[0])+CHARGE; sz,_=m.szrun(X,eps)
    old,_=h.build_hybrid(K); oldK=h.decode_hybrid(old)
    if not np.array_equal(oldK,K):raise RuntimeError('hybrid comparator mismatch')
    oldn=int(mb)+len(old)+CHARGE
    buf,outer,planes=encode(K); KD=decode(buf)
    if not np.array_equal(KD,K):raise RuntimeError('K mismatch')
    RD=aj.decode(KD,cd)
    if not np.array_equal(RD,R):raise RuntimeError('AR replay')
    err=float(np.max(np.abs(X-RD.astype(np.float64))))
    if err>eps*(1+5e-6):raise RuntimeError(('hard',err,eps))
    total=int(mb)+len(buf)+CHARGE
    out={'conditional_bytes':total,'hybrid_bytes':oldn,'ar32_bytes':base,'sz3_bytes':int(sz),'gain_vs_hybrid':oldn/total,'gain_vs_ar32':base/total,'gain_vs_sz3':sz/total,'address_bytes':len(buf),'outer':outer,'maxerr':err,'planes':planes}
    print(json.dumps(out,indent=2)); json.dump(out,open('imperial_ar32_conditional_bitplane_rank.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
