import json,math,os,sys
import numpy as np,segyio,zstandard as zstd
from scipy.signal import hilbert
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from research.garner_valley_das_full_benchmark import lattice_tile,enc_int,sz3_best,SPACE,TIME,SAFETY
from research.imperial_valley_frozen_brady_transfer import encode_tile

Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor();FS=200.0
STRIDES=(16,32,64,128);SHIFTS=(-1.0,0.0,1.0);QBITS=(8,16)

def phase_cycles(t):
    x=np.asarray(t,np.float64);p=np.zeros_like(x)
    a=(x>0)&(x<=30);p[a]=x[a]*x[a]/6.0
    b=(x>30)&(x<=60);p[b]=20*x[b]-300.0-x[b]*x[b]/6.0
    p[x>60]=300.0
    return p

def model(W,t0,eps,stride,shift,qbits):
    nt=W.shape[1];tt=(t0+np.arange(nt))/FS-shift;ph=2*np.pi*phase_cycles(tt);carrier=np.exp(-1j*ph)
    E=hilbert(W.astype(np.float64),axis=1)*carrier[None,:]
    idx=np.arange(0,nt,stride,dtype=np.int32)
    if idx[-1]!=nt-1:idx=np.append(idx,nt-1)
    C=E[:,idx]
    lim=127 if qbits==8 else 32767;dt=np.int8 if qbits==8 else np.int16
    scale=np.maximum(np.maximum(np.max(np.abs(C.real),axis=1),np.max(np.abs(C.imag),axis=1))/lim,1e-30).astype(np.float32)
    qr=np.rint(C.real/scale[:,None]).clip(-lim,lim).astype(dt);qi=np.rint(C.imag/scale[:,None]).clip(-lim,lim).astype(dt)
    coeff=np.stack([qr,qi],axis=-1)
    cb=Z.compress(coeff.tobytes());sb=Z.compress(scale.tobytes())
    cr=np.frombuffer(D.decompress(cb),dtype=dt,count=coeff.size).reshape(coeff.shape);sr=np.frombuffer(D.decompress(sb),np.float32,count=scale.size)
    Cd=(cr[...,0].astype(np.float64)+1j*cr[...,1].astype(np.float64))*sr[:,None]
    grid=np.arange(nt);Er=np.empty((W.shape[0],nt),np.float64);Ei=np.empty_like(Er)
    for c in range(W.shape[0]):
        Er[c]=np.interp(grid,idx,Cd[c].real);Ei[c]=np.interp(grid,idx,Cd[c].imag)
    Eh=Er+1j*Ei;P=np.real(Eh*np.exp(1j*ph)[None,:])
    step=2*eps*SAFETY;K=np.rint((W.astype(np.float64)-P)/step).astype(np.int32);kb,kr,Kd=enc_int(K);R=P+step*Kd;me=float(np.max(np.abs(W.astype(np.float64)-R)))
    if not np.all(np.isfinite(R)) or not math.isfinite(me) or me>eps*(1+5e-6):raise RuntimeError(('chirp hard',me,eps,stride,shift,qbits))
    total=len(cb)+len(sb)+kb+96
    return total,me,{'model_bytes':len(cb)+len(sb)+96,'correction_bytes':kb,'correction_nonzero':float(np.mean(K!=0)),'controls_per_channel':int(len(idx)),'stride':stride,'shift_s':shift,'qbits':qbits,'correction_rep':kr}

def main(path):
    with segyio.open(path,'r',ignore_geometry=True) as f:
        f.mmap();ntr=f.tracecount;ns=len(f.samples);A=np.stack([np.asarray(f.trace[i],np.float32) for i in range(ntr)])
    std=float(A.std(dtype=np.float64));eps=.1*std;internal=eps*SAFETY
    cps=sorted(set([0,max(0,(ntr-SPACE)//2),max(0,ntr-SPACE)]));tps=sorted(set([0,3072,6144,9216,max(0,ns-TIME)]));rows=[]
    for c0 in cps:
      for t0 in tps:
        W=np.ascontiguousarray(A[c0:c0+SPACE,t0:min(ns,t0+TIME)]);AT=np.ascontiguousarray(W.T);sb,so,sme=sz3_best(AT,eps);lb,lme,lnz,lrep=lattice_tile(W,eps,internal);blob,pme,pd=encode_tile(W,internal);pb=len(blob);best=None
        for stride in STRIDES:
          for shift in SHIFTS:
            for qb in QBITS:
              b,me,md=model(W,t0,eps,stride,shift,qb);r=(b,stride,shift,qb,me,md)
              if best is None or b<best[0]:best=r
        cb,stride,shift,qb,cme,cd=best
        rows.append({'c0':c0,'t0':t0,'shape':list(W.shape),'sz3_bytes':sb,'lattice_bytes':lb,'spectral_bytes':pb,'chirp_bytes':cb,'chirp_params':{'stride':stride,'shift_s':shift,'qbits':qb},'chirp_model_bytes':cd['model_bytes'],'chirp_correction_bytes':cd['correction_bytes'],'gains':{'lattice':sb/lb,'spectral':sb/pb,'chirp':sb/cb},'bps':{'sz3':8*sb/W.size,'lattice':8*lb/W.size,'spectral':8*pb/W.size,'chirp':8*cb/W.size},'lattice_transition_nonzero':lnz,'spectral_correction_nonzero':pd['correction_nonzero_fraction'],'chirp_correction_nonzero':cd['correction_nonzero'],'maxerr':{'sz3':sme,'lattice':lme,'spectral':pme,'chirp':cme}})
    S=sum(r['sz3_bytes'] for r in rows);samples=sum(np.prod(r['shape']) for r in rows);agg=[]
    for name in ('lattice','spectral','chirp'):
      b=sum(r[name+'_bytes'] for r in rows);agg.append({'method':name,'bytes':b,'sz3_bytes':S,'gain_vs_sz3':S/b,'bps':8*b/samples,'min_tile_gain':min(r['gains'][name] for r in rows),'median_tile_gain':float(np.median([r['gains'][name] for r in rows])),'max_tile_gain':max(r['gains'][name] for r in rows)})
    choices=[]
    for r in rows:
      vals=[('lattice',r['lattice_bytes']),('spectral',r['spectral_bytes']),('chirp',r['chirp_bytes'])];choices.append(min(vals,key=lambda x:x[1]))
    sel=np.array([{'lattice':0,'spectral':1,'chirp':2}[x[0]] for x in choices],np.uint8);packed=np.packbits(np.stack([(sel>>1)&1,sel&1],axis=1).ravel(),bitorder='little');selb=Z.compress(packed.tobytes());payload=sum(x[1] for x in choices);total=payload+len(selb)+8*len(rows)+128
    agg.append({'method':'adaptive3','bytes':total,'sz3_bytes':S,'gain_vs_sz3':S/total,'bps':8*total/samples,'selector_bytes':len(selb),'directory_bytes':8*len(rows),'counts':{k:sum(x[0]==k for x in choices) for k in ('lattice','spectral','chirp')}});agg.sort(key=lambda x:x['bytes'])
    out={'shape':[ntr,ns],'std':std,'eps':eps,'sample_rate_hz':FS,'sweep_model':'0->10 Hz in 30 s, then 10->0 Hz in 30 s','channel_positions':cps,'time_positions':tps,'aggregate':agg,'rows':rows,'scope':'Controlled-source chirp-envelope diagnostic. Encoder forms the analytic trace, removes a deterministic triangular chirp phase, and transmits only coarse complex envelope controls with explicitly serialized int8/int16 coefficients + per-channel scales. Decoder reconstructs the carrier from sample index and transmitted tiny shift/stride/mode parameters, interpolates the envelope, and receives a fully counted exact 2epsilon correction. Every final sample satisfies the unchanged full-array 10%-std hard error. Includes explicitly charged 3-language selector screen. Diagnostic only until full-array integration.'};print(json.dumps(out,indent=2),flush=True);json.dump(out,open('garner_chirp_envelope_fastgate.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
