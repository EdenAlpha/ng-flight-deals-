import json, math, sys
import h5py, numpy as np
from numba import njit
import imperial_dyadic_shared_resonator as ar
import imperial_decoder_phase_automaton as m

T0=14488
T=4096
C=32
TRAIN=1024
P=32
AR_STEP=267
REGIONS=(('hard',512),('easy',2304))
H_FACS=(1.0,1.25,1.5,1.75,1.999)
HEADER_BYTES=40
FINALISTS=24
INF=np.int64(1<<60)

@njit(cache=True)
def _eglen_signed(v):
    if v>=0:u=2*v
    else:u=-2*v-1
    n=u+1
    lg=0
    while n>1:
        n//=2;lg+=1
    return 2*lg+1

@njit(cache=True)
def _score_path(lo,hi,order):
    n=order.size
    prev=np.full(4,INF,np.int64)
    cur=np.full(4,INF,np.int64)
    idx0=order[0];a0=int(lo[idx0]);b0=int(hi[idx0]);ns0=b0-a0+1
    if ns0>4:return INF
    for j in range(ns0):prev[j]=_eglen_signed(a0+j)
    pn=ns0
    for i in range(1,n):
        idx=order[i];a=int(lo[idx]);b=int(hi[idx]);cn=b-a+1
        if cn>4:return INF
        for j in range(4):cur[j]=INF
        pidx=order[i-1];pa=int(lo[pidx])
        for j in range(cn):
            q=a+j;best=INF
            for k in range(pn):
                z=prev[k]+_eglen_signed(q-(pa+k))
                if z<best:best=z
            cur[j]=best
        for j in range(4):prev[j]=cur[j]
        pn=cn
    best=INF
    for j in range(pn):
        if prev[j]<best:best=prev[j]
    return best

@njit(cache=True)
def _recover_path(lo,hi,order):
    n=order.size
    back=np.full((n,4),-1,np.int8)
    prev=np.full(4,INF,np.int64)
    cur=np.full(4,INF,np.int64)
    idx0=order[0];a0=int(lo[idx0]);b0=int(hi[idx0]);pn=b0-a0+1
    for j in range(pn):prev[j]=_eglen_signed(a0+j)
    for i in range(1,n):
        idx=order[i];a=int(lo[idx]);cn=int(hi[idx])-a+1
        for j in range(4):cur[j]=INF
        pidx=order[i-1];pa=int(lo[pidx])
        for j in range(cn):
            q=a+j;best=INF;bk=-1
            for k in range(pn):
                z=prev[k]+_eglen_signed(q-(pa+k))
                if z<best:best=z;bk=k
            cur[j]=best;back[i,j]=bk
        for j in range(4):prev[j]=cur[j]
        pn=cn
    bj=0;best=prev[0]
    for j in range(1,pn):
        if prev[j]<best:best=prev[j];bj=j
    out=np.empty(n,np.int32)
    j=bj
    for i in range(n-1,-1,-1):
        idx=order[i];out[i]=int(lo[idx])+j
        if i>0:j=int(back[i,j])
    return best,out

def _write_eg_signed(vals):
    out=bytearray();acc=0;nb=0
    def put(bit):
        nonlocal acc,nb
        acc=(acc<<1)|(1 if bit else 0);nb+=1
        if nb==8:
            out.append(acc);acc=0;nb=0
    for vv in vals:
        v=int(vv);u=2*v if v>=0 else -2*v-1;n=u+1;lg=n.bit_length()-1
        for _ in range(lg):put(0)
        for k in range(lg,-1,-1):put((n>>k)&1)
    if nb:
        out.append(acc<<(8-nb))
    return bytes(out)

def _read_eg_signed(blob,nvals):
    total=len(blob)*8;pos=0;out=np.empty(nvals,np.int32)
    def bitat(p):return (blob[p>>3]>>(7-(p&7)))&1
    for i in range(nvals):
        z=0
        while pos<total and bitat(pos)==0:
            z+=1;pos+=1
        if pos>=total:raise RuntimeError('eg eof unary')
        pos+=1;n=1
        for _ in range(z):
            if pos>=total:raise RuntimeError('eg eof suffix')
            n=(n<<1)|bitat(pos);pos+=1
        u=n-1
        out[i]=(u>>1) if (u&1)==0 else -((u>>1)+1)
    return out

def encode_address(qpath):
    d=np.empty_like(qpath)
    d[0]=qpath[0];d[1:]=qpath[1:]-qpath[:-1]
    raw=_write_eg_signed(d)
    z=m.Z.compress(raw)
    if len(z)<len(raw):
        rep='eg+zstd';stored=z;decoded_raw=m.D.decompress(z)
    else:
        rep='eg';stored=raw;decoded_raw=raw
    dd=_read_eg_signed(decoded_raw,len(qpath))
    qq=np.cumsum(dd,dtype=np.int64).astype(np.int32)
    if not np.array_equal(qq,qpath):raise RuntimeError('address roundtrip')
    return stored,rep,len(raw),qq

def path_bank(C,T):
    paths=[]
    def add(name,seq):
        a=np.asarray(seq,np.int64)
        if a.size!=C*T or np.unique(a).size!=a.size:raise RuntimeError(('bad path',name,a.size,np.unique(a).size))
        paths.append((name,a))
    add('channel-major',[c*T+t for c in range(C) for t in range(T)])
    add('channel-snake',[c*T+(t if c%2==0 else T-1-t) for c in range(C) for t in range(T)])
    add('time-major',[c*T+t for t in range(T) for c in range(C)])
    add('time-snake',[(c if t%2==0 else C-1-c)*T+t for t in range(T) for c in range(C)])
    for B in (8,16,32,64,128,256):
        seq=[]
        for bi,t0 in enumerate(range(0,T,B)):
            t1=min(T,t0+B)
            cr=range(C) if bi%2==0 else range(C-1,-1,-1)
            for ci,c in enumerate(cr):
                ts=range(t0,t1) if (ci+bi)%2==0 else range(t1-1,t0-1,-1)
                for t in ts:seq.append(c*T+t)
        add(f'block-snake-{B}',seq)
    for s in (-4,-2,-1,1,2,4):
        seq=[]
        for t in range(T):
            sh=(s*t)%C
            for j in range(C):
                c=(j+sh)%C
                seq.append(c*T+t)
        add(f'time-shear-{s}',seq)
    for s in (1,2,4,8,16,32,64):
        seq=[]
        for c in range(C):
            sh=(s*c)%T
            for j in range(T):seq.append(c*T+((j+sh)%T))
        add(f'channel-phase-{s}',seq)
    return paths

def legal_bounds(X,eps,h):
    flat=np.asarray(X,np.float64).reshape(-1)
    b=eps*(1-1e-12)
    lo=np.ceil((flat-b)/h).astype(np.int32)
    hi=np.floor((flat+b)/h).astype(np.int32)
    if np.any(lo>hi):raise RuntimeError('empty legal set')
    width=hi.astype(np.int64)-lo.astype(np.int64)+1
    if int(width.max())>4:raise RuntimeError(('too many legal states',int(width.max()),h/eps))
    return lo,hi

def ar32_baseline(X,eps):
    co=ar.fit_shared(X[:,:TRAIN],P);mb,cd=ar.model_frame(co)
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):
            pred=ar.predict_hist(R,c,t,cd,P,'shared')
            k=int(np.rint((float(X[c,t])-pred)/AR_STEP));rr=pred+AR_STEP*k
            R[c,t]=rr;K[c,t]=k
    fr=m.encode_k(K);Kd=fr[2]
    Rd=np.zeros_like(R)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):Rd[c,t]=ar.predict_hist(Rd,c,t,cd,P,'shared')+AR_STEP*int(Kd[c,t])
    if not np.array_equal(Rd,R):raise RuntimeError('ar32 replay')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('ar32 hard',me,eps))
    total=int(mb)+int(fr[0])+32
    return {'bytes':total,'bps':8*total/X.size,'model_bytes':int(mb),'innovation_bytes':int(fr[0]),'rep':fr[1],'maxerr':me}

def solve_region(name,X,eps,paths):
    szb,ori=m.szrun(X,eps);arb=ar32_baseline(X,eps);scores=[]
    for fi,fac in enumerate(H_FACS):
        h=float(eps*fac);lo,hi=legal_bounds(X,eps,h)
        for si,(pname,order) in enumerate(paths):
            bits=int(_score_path(lo,hi,order))
            scores.append({'fac':fac,'fac_id':fi,'seed':si,'path':pname,'raw_eg_bits':bits,'raw_eg_bytes':(bits+7)//8+HEADER_BYTES})
    scores.sort(key=lambda r:r['raw_eg_bytes'])
    exact=[]
    for cand in scores[:FINALISTS]:
        fac=cand['fac'];h=float(eps*fac);lo,hi=legal_bounds(X,eps,h);order=paths[cand['seed']][1]
        bits,qpath=_recover_path(lo,hi,order)
        stored,rep,rawlen,qd=encode_address(qpath)
        if int(bits)!=cand['raw_eg_bits']:raise RuntimeError('score drift')
        Q=np.empty(X.size,np.int32);Q[order]=qd;Q=Q.reshape(X.shape)
        R=Q.astype(np.float64)*h;me=float(np.max(np.abs(X-R)))
        if me>eps*(1+5e-6):raise RuntimeError(('nova hard',name,me,eps))
        total=len(stored)+HEADER_BYTES
        exact.append({**cand,'bytes':total,'bps':8*total/X.size,'address_rep':rep,'raw_eg_payload_bytes':rawlen,'stored_payload_bytes':len(stored),'maxerr':me,'gain_vs_sz3':szb/total,'gain_vs_ar32':arb['bytes']/total})
    exact.sort(key=lambda r:r['bytes']);best=exact[0]
    return {'region':name,'shape':list(X.shape),'samples':int(X.size),'local_std':float(X.std()),'eps':eps,'sz3':{'bytes':int(szb),'bps':8*szb/X.size,'orientation':ori},'ar32':arb,'best':best,'top_exact':exact[:12],'screened_configs':len(scores)}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic']
        if tuple(d.shape)!=(30000,6912):raise RuntimeError(('shape',d.shape))
        _,std=m.stats(d);eps=.1*std;paths=path_bank(C,T);rows=[]
        for name,c0 in REGIONS:
            X=np.asarray(d[T0:T0+T,c0:c0+C],np.float64).T
            r=solve_region(name,X,eps,paths);rows.append(r);print(json.dumps(r,indent=2),flush=True)
    out={'global_std':std,'eps':eps,'tile_t0':T0,'shape':[C,T],'path_count':len(paths),'h_factors':list(H_FACS),'header_bytes':HEADER_BYTES,'finalists_materialized':FINALISTS,'rows':rows,'scope':'Decoder-real NOVA/global-coordinate address gate. Each candidate selector chooses one deterministic whole-object spacetime coordinate path and one public lattice spacing. Every source sample contributes its exact legal reconstruction interval under the unchanged +/-epsilon contract. Dynamic programming then chooses the globally minimum signed Exp-Golomb address along the entire path; this is a real emitted code objective, not summed heuristic restriction bits or -log legal-set mass. The emitted signed-delta Exp-Golomb stream is actually serialized and independently parsed; an optional Zstd pass compresses the address itself and is byte-decoded before address reconstruction. The seed/factor/framing are covered by a conservative fixed header charge. The decoder maps the recovered address back through the public path, reconstructs the physical array and verifies the hard bound. The best actual stream is compared with matched SZ3 and a decoder-real shared AR32 step267 baseline on the identical tile. This is a coordinate/address representation test, not a predictor oracle and not yet a whole-file promotion.'}
    json.dump(out,open('imperial_nova_global_coordinate_address.json','w'),indent=2)
    print(json.dumps({'summary':[{'region':r['region'],'nova_bytes':r['best']['bytes'],'ar32_bytes':r['ar32']['bytes'],'sz3_bytes':r['sz3']['bytes'],'gain_vs_ar32':r['best']['gain_vs_ar32'],'gain_vs_sz3':r['best']['gain_vs_sz3'],'path':r['best']['path'],'hfac':r['best']['fac'],'rep':r['best']['address_rep']} for r in rows]},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
