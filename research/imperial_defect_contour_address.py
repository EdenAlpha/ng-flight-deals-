import json,sys,struct
import h5py,numpy as np
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

MODES=('raw','xort','xors','xor2d','edge','majority')


def _symbol_pred(A,c,t,mode):
    l=int(A[c-1,t]) if c>0 else 0
    u=int(A[c,t-1]) if t>0 else 0
    d=int(A[c-1,t-1]) if c>0 and t>0 else 0
    if mode=='med':
        if d>=max(l,u): return min(l,u)
        if d<=min(l,u): return max(l,u)
        return l+u-d
    if mode=='paeth':
        p=l+u-d;pl=abs(p-l);pu=abs(p-u);pd=abs(p-d)
        return l if pl<=pu and pl<=pd else (u if pu<=pd else d)
    raise ValueError(mode)


def predictor_frame(A,mode):
    A=np.asarray(A,np.int32);R=np.empty_like(A)
    for t in range(A.shape[1]):
        for c in range(A.shape[0]):R[c,t]=int(A[c,t])-_symbol_pred(A,c,t,mode)
    fr=m.encode_k(R);Rd=np.asarray(fr[2],np.int32);Ad=np.empty_like(A)
    for t in range(A.shape[1]):
        for c in range(A.shape[0]):Ad[c,t]=_symbol_pred(Ad,c,t,mode)+int(Rd[c,t])
    if not np.array_equal(Ad,A):raise RuntimeError(('predictor replay',mode))
    return int(fr[0])+8,mode+'+'+fr[1],Ad


def _transform(B,mode):
    B=np.asarray(B,np.uint8)
    if mode=='raw':return B.copy()
    if mode=='xort':
        X=B.copy();X[:,1:]^=B[:,:-1];return X
    if mode=='xors':
        X=B.copy();X[1:,:]^=B[:-1,:];return X
    if mode=='xor2d':
        X=B.copy()
        if B.shape[1]>1:X[0,1:]=B[0,1:]^B[0,:-1]
        if B.shape[0]>1:X[1:,0]=B[1:,0]^B[:-1,0]
        if B.shape[0]>1 and B.shape[1]>1:X[1:,1:]=B[1:,1:]^B[:-1,1:]^B[1:,:-1]^B[:-1,:-1]
        return X
    X=np.empty_like(B)
    for t in range(B.shape[1]):
        for c in range(B.shape[0]):
            l=int(B[c-1,t]) if c else 0;u=int(B[c,t-1]) if t else 0;d=int(B[c-1,t-1]) if c and t else 0
            if mode=='edge':p=l if l==u else d
            elif mode=='majority':p=1 if l+u+d>=2 else 0
            else:raise ValueError(mode)
            X[c,t]=int(B[c,t])^p
    return X


def _inverse(X,mode):
    X=np.asarray(X,np.uint8)
    if mode=='raw':return X.copy()
    if mode=='xort':return np.bitwise_xor.accumulate(X,axis=1).astype(np.uint8)
    if mode=='xors':return np.bitwise_xor.accumulate(X,axis=0).astype(np.uint8)
    if mode=='xor2d':
        return np.bitwise_xor.accumulate(np.bitwise_xor.accumulate(X,axis=0),axis=1).astype(np.uint8)
    B=np.empty_like(X)
    for t in range(X.shape[1]):
        for c in range(X.shape[0]):
            l=int(B[c-1,t]) if c else 0;u=int(B[c,t-1]) if t else 0;d=int(B[c-1,t-1]) if c and t else 0
            if mode=='edge':p=l if l==u else d
            elif mode=='majority':p=1 if l+u+d>=2 else 0
            else:raise ValueError(mode)
            B[c,t]=int(X[c,t])^p
    return B


def _put_uvar(out,x):
    x=int(x)
    while x>=128:out.append((x&127)|128);x>>=7
    out.append(x)


def _get_uvar(buf,pos):
    x=0;s=0
    while True:
        b=buf[pos];pos+=1;x|=(b&127)<<s
        if b<128:return x,pos
        s+=7


def _gap_payload(X):
    pos=np.flatnonzero(np.asarray(X,np.uint8).ravel())
    out=bytearray(struct.pack('<I',int(pos.size)));prev=-1
    for p in pos:
        _put_uvar(out,int(p)-prev);prev=int(p)
    return bytes(out)


def _gap_decode(raw,n):
    cnt=struct.unpack_from('<I',raw,0)[0];p=4;prev=-1;flat=np.zeros(n,np.uint8)
    for _ in range(cnt):
        d,p=_get_uvar(raw,p);prev+=d
        if prev<0 or prev>=n:raise RuntimeError('gap range')
        flat[prev]=1
    if p!=len(raw):raise RuntimeError(('gap trailing',p,len(raw)))
    return flat


def bitplane_contour_frame(A):
    A=np.asarray(A,np.int32);u=m.zig(A);mx=int(u.max()) if u.size else 0;nb=max(1,mx.bit_length());n=A.size
    stream=bytearray(struct.pack('<4sHHB',b'BPC1',A.shape[0],A.shape[1],nb));chosen=[]
    for bit in range(nb):
        B=((u>>bit)&1).astype(np.uint8);best=None
        for mi,mode in enumerate(MODES):
            X=_transform(B,mode)
            packed=np.packbits(X.ravel(),bitorder='little').tobytes()
            for method,raw in ((0,packed),(1,_gap_payload(X))):
                z=m.Z.compress(raw);score=len(z)+6
                if best is None or score<best[0]:best=(score,mi,method,z,mode,int(X.sum()))
        _,mi,method,z,mode,ones=best
        stream.extend(struct.pack('<BBI',mi,method,len(z)));stream.extend(z);chosen.append({'bit':bit,'mode':mode,'method':'packed' if method==0 else 'gaps','stored':len(z),'boundary_ones':ones})
    buf=bytes(stream);off=0;magic,nc,nt,nb2=struct.unpack_from('<4sHHB',buf,off);off+=9
    if magic!=b'BPC1' or (nc,nt)!=(A.shape[0],A.shape[1]) or nb2!=nb:raise RuntimeError('bp header')
    uu=np.zeros(n,np.uint64)
    for bit in range(nb):
        mi,method,L=struct.unpack_from('<BBI',buf,off);off+=6;z=buf[off:off+L];off+=L;raw=m.D.decompress(z)
        if method==0:X=np.unpackbits(np.frombuffer(raw,np.uint8),bitorder='little')[:n].astype(np.uint8)
        elif method==1:X=_gap_decode(raw,n)
        else:raise RuntimeError('bp method')
        X=X.reshape(A.shape);B=_inverse(X,MODES[mi]);uu|=B.ravel().astype(np.uint64)<<bit
    if off!=len(buf):raise RuntimeError('bp trailing')
    Ad=m.unzig(uu.reshape(A.shape)).astype(np.int32)
    if not np.array_equal(Ad,A):raise RuntimeError('bp contour replay')
    return len(buf),'bitplane_contour',Ad,chosen


def build_resonant(X,eps):
    h=float(eps*1.5);lo,hi=g.legal_q(X,eps,h);Q=g._initial(lo,hi,0);changes=0
    for _ in range(g.ROUNDS):
        dts,dcs,co,intercept=g.fit_model(Q)
        Q,D,H,score,nz,ch=g._optimize_from(Q,lo,hi,dts,dcs,co,intercept,g.SCALE,False,g.PASSES);changes+=int(ch)
    dts,dcs,co,intercept=g.fit_model(Q)
    Q,D,H,score,nz,ch=g._optimize_from(Q,lo,hi,dts,dcs,co,intercept,g.SCALE,False,g.PASSES);changes+=int(ch)
    return h,Q,D,dts,dcs,co,intercept,score,nz,changes


def validate(X,eps,h,Q,Ed,dts,dcs,co,intercept,defect_bytes,rep,extra=None):
    mb,mrep,ddt,ddc,dco,dinter=g.model_frame(dts,dcs,co,intercept);Qd=np.empty_like(Q)
    for t in range(g.T):
        for c in range(g.C):Qd[c,t]=g._pred(Qd,c,t,ddt,ddc,dco,dinter,g.SCALE)+int(Ed[c,t])
    if not np.array_equal(Qd,Q):raise RuntimeError(('Q replay',rep))
    me=float(np.max(np.abs(X-Qd.astype(np.float64)*h)))
    if me>eps*(1+5e-6):raise RuntimeError(('hard',rep,me,eps))
    total=int(mb)+int(defect_bytes)+g.HEADER
    r={'rep':rep,'bytes':total,'bps':8*total/X.size,'model_bytes':int(mb),'defect_bytes':int(defect_bytes),'maxerr':me,'defect_zero_fraction':float(np.mean(Ed==0))}
    if extra is not None:r['detail']=extra
    return r


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);arb=g.ar32_baseline(X,eps);h,Q,E,dts,dcs,co,intercept,score,nz,changes=build_resonant(X,eps)
    rows=[]
    fr=m.encode_k(E);rows.append(validate(X,eps,h,Q,np.asarray(fr[2],np.int32),dts,dcs,co,intercept,int(fr[0]),'baseline_'+fr[1]))
    for mode in ('med','paeth'):
        b,rep,Ed=predictor_frame(E,mode);rows.append(validate(X,eps,h,Q,Ed,dts,dcs,co,intercept,b,rep))
    b,rep,Ed,detail=bitplane_contour_frame(E);rows.append(validate(X,eps,h,Q,Ed,dts,dcs,co,intercept,b,rep,detail))
    for r in rows:
        r['gain_vs_sz3']=szb/r['bytes'];r['gain_vs_ar32']=arb['bytes']/r['bytes'];print(json.dumps({k:v for k,v in r.items() if k!='detail'},indent=2),flush=True)
    rows.sort(key=lambda x:x['bytes']);best=rows[0]
    out={'region':'hard','shape':[g.C,g.T],'samples':int(X.size),'global_std':std,'eps':eps,'h':h,'hfac':1.5,'sz3':{'bytes':int(szb),'bps':8*szb/X.size,'orientation':ori},'ar32':arb,'learned_generator':{'taps':[[int(a),int(b)] for a,b in zip(dts,dcs)],'coef_q12':[int(x) for x in co],'intercept_q12':int(intercept),'surrogate_bits':int(score),'defect_nonzeros':int(nz),'optimizer_changes':int(changes)},'rows':rows,'best':best,'scope':'Decoder-real higher-level witness representation gate after PR498. The exact same charged learned sparse generator and globally legal h=1.5epsilon reconstruction are rebuilt. No generator or hard-box result is changed. Only the final dense defect witness representation changes. Candidates include causal MED and Paeth contour prediction followed by the incumbent exact representation menu, plus a literal byte stream that zigzags defect symbols into bitplanes and chooses per plane among raw, temporal boundary, spatial boundary, 2-D XOR boundary, causal edge, and causal majority maps; each transformed plane chooses packed bits or explicit gap addresses, is Zstd serialized, parsed, inverse-transformed, and must reproduce the identical defect raster. The decoded defect plus decoded charged generator must reproduce the exact Q field and satisfy the unchanged source-domain hard error. This tests geometry/topology of witness classes rather than another source predictor.'}
    json.dump(out,open('imperial_defect_contour_address.json','w'),indent=2)
    print(json.dumps({'summary':{'best_rep':best['rep'],'bytes':best['bytes'],'ar32_bytes':arb['bytes'],'sz3_bytes':int(szb),'gain_ar32':best['gain_vs_ar32'],'gain_sz3':best['gain_vs_sz3'],'baseline_defect_bytes':rows[[x['rep'].startswith('baseline_') for x in rows].index(True)]['defect_bytes'] if any(x['rep'].startswith('baseline_') for x in rows) else None}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])