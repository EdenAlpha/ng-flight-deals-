import json,os,struct,sys
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import h5py,numpy as np,zstandard as zstd
from pysz import sz,szConfig,szErrorBoundMode
from research.imperial_valley_frozen_brady_transfer import correction_candidates,decode_correction,SAFETY

EPSF=1-1e-6
MAG=b'IVGAU001'
MH='<8sBBHHIII f'
MHS=struct.calcsize(MH)
ZC=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()

def z(raw):return ZC.compress(raw)
def uz(b):return ZD.decompress(b)

def deriv(U):
    D=np.empty_like(U,np.float32);D[:,0]=U[:,0];D[:,1:]=U[:,1:]-U[:,:-1];return D

def encode_model(U,N,qmode):
    nc,nt=U.shape;C=np.fft.rfft2(U.astype(np.float64));flat=C.ravel();n=min(N,flat.size)
    ii=np.argpartition(np.abs(flat),-n)[-n:] if n<flat.size else np.arange(flat.size);ii=np.sort(ii).astype(np.uint32);v=flat[ii]
    ib=z(ii.tobytes())
    if qmode=='i8':
        xy=np.stack([v.real,v.imag],axis=1);scale=np.float32(max(float(np.max(np.abs(xy)))/127.0,1e-30));q=np.clip(np.rint(xy/float(scale)),-127,127).astype(np.int8);vb=z(q.tobytes());mode=0
    else:
        scale=np.float32(0.0);vv=np.stack([v.real,v.imag],axis=1).astype(np.float32);vb=z(vv.tobytes());mode=1
    hdr=struct.pack(MH,MAG,1,mode,nc,nt,n,len(ib),len(vb),float(scale));blob=hdr+ib+vb
    return blob,decode_model(blob)

def decode_model(blob):
    magic,ver,mode,nc,nt,n,li,lv,scale=struct.unpack(MH,blob[:MHS]);assert magic==MAG and ver==1
    p=MHS;ii=np.frombuffer(uz(blob[p:p+li]),np.uint32,count=n).astype(np.int64);p+=li;vb=blob[p:p+lv];p+=lv;assert p==len(blob)
    if mode==0:
        q=np.frombuffer(uz(vb),np.int8,count=n*2).reshape(n,2);v=(q[:,0].astype(np.float32)+1j*q[:,1].astype(np.float32))*np.float32(scale)
    else:
        q=np.frombuffer(uz(vb),np.float32,count=n*2).reshape(n,2);v=q[:,0].astype(np.float32)+1j*q[:,1].astype(np.float32)
    C=np.zeros((nc,nt//2+1),np.complex128).ravel();C[ii]=v.astype(np.complex128);C=C.reshape(nc,nt//2+1)
    return np.fft.irfft2(C,s=(nc,nt)).astype(np.float32)

def encode_corr(Q):
    best,_=correction_candidates(Q);_,mode,c,b1,b2=best
    hdr=struct.pack('<BBII',mode,c,len(b1),len(b2));return hdr+b1+b2

def decode_corr(blob,shape):
    mode,c,l1,l2=struct.unpack('<BBII',blob[:10]);b1=blob[10:10+l1];b2=blob[10+l1:10+l1+l2];assert 10+l1+l2==len(blob)
    return decode_correction(mode,c,b1,b2,shape)

def candidate(W,eps,N,qmode,niter):
    internal=eps*SAFETY;U=np.cumsum(W.astype(np.float64),axis=1)
    for _ in range(niter):
        mb,P=encode_model(U,N,qmode);pred=deriv(P)
        legal=np.clip(pred,W-internal,W+internal)
        U=np.cumsum(legal.astype(np.float64),axis=1)
    mb,P=encode_model(U,N,qmode);pred=deriv(P);step=2*internal*EPSF
    Q=np.rint((W.astype(np.float64)-pred.astype(np.float64))/step).astype(np.int32);cb=encode_corr(Q)
    # byte-decode both model and correction before accepting bytes
    Pd=decode_model(mb);Qd=decode_corr(cb,W.shape);R=deriv(Pd)+Qd.astype(np.float32)*np.float32(step)
    me=float(np.max(np.abs(W-R)))
    if me>eps*(1+3e-6):raise RuntimeError(('hard error',N,qmode,niter,me,eps))
    return {'N':N,'qmode':qmode,'iterations':niter,'bytes':len(mb)+len(cb)+16,'model_bytes':len(mb),'correction_bytes':len(cb),'correction_nonzero_fraction':float(np.mean(Q!=0)),'maxerr':me}

def matched_sz3(W,eps):
    cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps);best=None
    for name,A in [('ct',np.ascontiguousarray(W)),('tc',np.ascontiguousarray(W.T))]:
        b,_=sz.compress(A,cfg);R,_=sz.decompress(b,np.float32,A.shape);me=float(np.max(np.abs(A-R)))
        if me>eps*(1+3e-6):raise RuntimeError(('sz3',me,eps))
        row={'orientation':name,'bytes':int(b.size),'maxerr':me}
        if best is None or row['bytes']<best['bytes']:best=row
    return best

def stats(d):
    s=ss=0.;n=0
    for t in range(0,d.shape[0],2048):
        x=np.asarray(d[t:min(t+2048,d.shape[0])],np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
    m=s/n;return float(np.sqrt(max(0,ss/n-m*m)))

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];std=stats(d);eps=.1*std
        ts=np.linspace(0,d.shape[0]-1024,3,dtype=int);cs=np.linspace(0,d.shape[1]-128,3,dtype=int)
        rows=[];tiles=[]
        for t0 in ts:
          for c0 in cs:
            W=np.asarray(d[t0:t0+1024,c0:c0+128]).T.astype(np.float32);base=matched_sz3(W,eps);tid=f't{t0}c{c0}';tiles.append({'id':tid,'sz3':base['bytes'],'native_bytes':int(W.size*2)})
            for N in [64,128,256,512,1024]:
              for qm in ['i8','f32']:
                for it in [0,1,3,8]:
                  r=candidate(W,eps,N,qm,it);r.update({'tile':tid,'sz3':base['bytes'],'gain_vs_sz3':base['bytes']/r['bytes']});rows.append(r)
            b=max((x for x in rows if x['tile']==tid),key=lambda x:x['gain_vs_sz3']);print(json.dumps({'tile':tid,'best':b}),flush=True)
        combos=[]
        keys=sorted(set((r['N'],r['qmode'],r['iterations']) for r in rows))
        for key in keys:
            rr=[r for r in rows if (r['N'],r['qmode'],r['iterations'])==key];cb=sum(r['bytes'] for r in rr);sb=sum(r['sz3'] for r in rr)
            combos.append({'N':key[0],'qmode':key[1],'iterations':key[2],'bytes':cb,'sz3':sb,'gain_vs_sz3':sb/cb,'median_correction_nonzero_fraction':float(np.median([r['correction_nonzero_fraction'] for r in rr])),'min_tile_gain':min(r['gain_vs_sz3'] for r in rr),'max_tile_gain':max(r['gain_vs_sz3'] for r in rr)})
        combos.sort(key=lambda r:r['gain_vs_sz3'],reverse=True);oracle=sum(min((r for r in rows if r['tile']==t['id']),key=lambda x:x['bytes'])['bytes'] for t in tiles);sb=sum(t['sz3'] for t in tiles)
        out={'std':std,'eps':eps,'tiles':tiles,'best_global':combos[0],'top_combos':combos[:20],'oracle_per_tile_bytes':oracle,'oracle_gain_vs_sz3':sb/oracle,'rows':rows,'scope':'9-tile exact self-decoding screen; sparse latent potential is optimized by alternating projection against derivative-domain legal intervals; no potential-domain error bound is imposed'}
        print(json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2),flush=True);json.dump(out,open('imperial_gauge_spectral_projection.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
