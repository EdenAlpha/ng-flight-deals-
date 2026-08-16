import json,sys,struct
import h5py,numpy as np
import imperial_dyadic_shared_resonator as ar
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

P=32
STEP=267
VERSION=1


def put_uvar(out,x):
    x=int(x)
    while x>=128:out.append((x&127)|128);x>>=7
    out.append(x)

def get_uvar(buf,pos):
    x=0;s=0
    while True:
        if pos>=len(buf):raise RuntimeError('uvar eof')
        b=buf[pos];pos+=1;x|=(b&127)<<s
        if b<128:return x,pos
        s+=7


def model_variants(co):
    a=np.asarray(co,np.float32);raw=a.tobytes();bits=a.view(np.uint32)
    variants=[]
    variants.append(('raw',raw))
    variants.append(('zstd',ar.Z.compress(raw)))
    x=bits.copy();x[1:]^=bits[:-1];variants.append(('xor32_zstd',ar.Z.compress(x.tobytes())))
    d=np.empty_like(bits);d[0]=bits[0];d[1:]=bits[1:]-bits[:-1];variants.append(('delta32_zstd',ar.Z.compress(d.tobytes())))
    bp=np.frombuffer(raw,np.uint8).reshape(a.size,4).T.copy();variants.append(('byteplanes_zstd',ar.Z.compress(bp.tobytes())))
    return variants


def encode_model(co):
    cand=[]
    for mi,(name,payload) in enumerate(model_variants(co)):
        out=bytearray([mi]);put_uvar(out,len(payload));out.extend(payload);cand.append((len(out),bytes(out),name))
    _,buf,name=min(cand,key=lambda z:z[0]);return buf,name


def decode_model(buf,pos,ncoef):
    mi=int(buf[pos]);pos+=1;L,pos=get_uvar(buf,pos);payload=bytes(buf[pos:pos+L]);pos+=L
    if len(payload)!=L:raise RuntimeError('model eof')
    if mi==0:raw=payload
    elif mi==1:raw=ar.D.decompress(payload)
    elif mi==2:
        x=np.frombuffer(ar.D.decompress(payload),np.uint32,count=ncoef).copy();b=x.copy()
        for i in range(1,ncoef):b[i]^=b[i-1]
        raw=b.tobytes()
    elif mi==3:
        d=np.frombuffer(ar.D.decompress(payload),np.uint32,count=ncoef).copy();b=np.cumsum(d,dtype=np.uint32);raw=b.tobytes()
    elif mi==4:
        bp=np.frombuffer(ar.D.decompress(payload),np.uint8,count=ncoef*4).reshape(4,ncoef);raw=bp.T.copy().tobytes()
    else:raise RuntimeError('model mode')
    a=np.frombuffer(raw,np.float32,count=ncoef).copy()
    if a.size!=ncoef:raise RuntimeError('model size')
    return a,pos


def encode_k_compact(K):
    K=np.asarray(K,np.int32);u=m.zig(K);mx=int(u.max()) if u.size else 0;nb=max(1,mx.bit_length());out=bytearray([nb]);detail=[]
    nbytes=(u.size+7)//8
    for bit in range(nb):
        packed=np.packbits(((u.ravel()>>bit)&1).astype(np.uint8),bitorder='little').tobytes();z=m.Z.compress(packed)
        if len(z)+2 < len(packed)+1:
            out.append(1);put_uvar(out,len(z));out.extend(z);method='zstd';L=len(z)
        else:
            out.append(0);out.extend(packed);method='raw';L=len(packed)
        detail.append({'bit':bit,'method':method,'payload_bytes':L})
    return bytes(out),detail


def decode_k_compact(buf,pos,shape):
    nb=int(buf[pos]);pos+=1;n=int(np.prod(shape));nbytes=(n+7)//8;u=np.zeros(n,np.uint64)
    for bit in range(nb):
        mode=int(buf[pos]);pos+=1
        if mode==0:
            raw=bytes(buf[pos:pos+nbytes]);pos+=nbytes
        elif mode==1:
            L,pos=get_uvar(buf,pos);raw=m.D.decompress(bytes(buf[pos:pos+L]));pos+=L
        else:raise RuntimeError('k mode')
        B=np.unpackbits(np.frombuffer(raw,np.uint8),bitorder='little')[:n].astype(np.uint64);u|=B<<bit
    return m.unzig(u.reshape(shape)).astype(np.int32),pos


def build_ar32(X):
    co=ar.fit_shared(X[:,:g.TRAIN],P);R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for c0 in range(X.shape[0]):
        for t in range(X.shape[1]):
            pred=ar.predict_hist(R,c0,t,co,P,'shared');k=int(np.rint((float(X[c0,t])-pred)/STEP));R[c0,t]=pred+STEP*k;K[c0,t]=k
    return co,R,K


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std;X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    old=g.ar32_baseline(X,eps);szb,ori=m.szrun(X,eps);co,R,K=build_ar32(X)
    model,mname=encode_model(co);kf,kdetail=encode_k_compact(K);stream=bytes([VERSION])+model+kf
    pos=0
    if stream[pos]!=VERSION:raise RuntimeError('version')
    pos+=1;cod,pos=decode_model(stream,pos,P+1);Kd,pos=decode_k_compact(stream,pos,X.shape)
    if pos!=len(stream):raise RuntimeError(('trailing',pos,len(stream)))
    if not np.array_equal(cod.view(np.uint32),np.asarray(co,np.float32).view(np.uint32)):raise RuntimeError('coef mismatch')
    if not np.array_equal(Kd,K):raise RuntimeError('K mismatch')
    Rd=np.zeros_like(R)
    for c0 in range(X.shape[0]):
        for t in range(X.shape[1]):Rd[c0,t]=ar.predict_hist(Rd,c0,t,cod,P,'shared')+STEP*int(Kd[c0,t])
    if not np.array_equal(Rd,R):raise RuntimeError('AR reconstruction mismatch')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('hard',me,eps))
    total=len(stream);r={'bytes':total,'bps':8*total/X.size,'model_bytes':len(model),'innovation_bytes':len(kf),'version_bytes':1,'model_rep':mname,'maxerr':me,'delta_vs_old':total-old['bytes']}
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'public_codec_config':{'P':P,'step':STEP,'shape_external':True,'epsilon_external':True,'kind':'shared_AR32'},'sz3':{'bytes':int(szb),'orientation':ori},'old_ar32':old,'compact_ar32':r,'k_detail':kdetail,'scope':'Fair compact-container audit of the same charged AR32 algorithm used as the Imperial hard-tile incumbent. Shape and epsilon are external decode arguments under the same convention used by SZ3 and compact NOVA. The exact 33 float32 AR32 coefficients are losslessly represented by the smallest charged public representation among raw, Zstd, XOR32+Zstd, delta32+Zstd and byte-plane+Zstd, with selector and payload length stored. The exact zigzag K field is encoded as real bitplanes with per-plane raw/Zstd choice and compact lengths. A literal stream is parsed to EOF; coefficient bit patterns and K are recovered exactly, recursive AR reconstruction is reproduced exactly, and hard error is verified. No algorithmic change or approximate coefficient quantization is allowed.'};json.dump(out,open('imperial_compact_ar32_audit.json','w'),indent=2)
    print(json.dumps({'summary':{'old_ar32':old['bytes'],'compact_ar32':total,'delta':total-old['bytes'],'model':len(model),'innovation':len(kf),'model_rep':mname,'sz3':int(szb),'maxerr':me}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
