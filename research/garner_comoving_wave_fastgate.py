import json,math,os,sys
import numpy as np,segyio,zstandard as zstd
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from research.garner_valley_das_full_benchmark import lattice_tile,encode_tile,sz3_best,SPACE,TIME,SAFETY

Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor();MAXLAG=96

def align(W):
    X=W.astype(np.float64);Xc=X-X.mean(axis=1,keepdims=True);ref=Xc[X.shape[0]//2]
    F=np.fft.rfft(Xc,axis=1);R=F*np.conj(np.fft.rfft(ref))[None,:];cc=np.fft.irfft(R,n=X.shape[1],axis=1)
    idx=np.concatenate((np.arange(0,MAXLAG+1),np.arange(X.shape[1]-MAXLAG,X.shape[1])))
    sub=cc[:,idx];j=np.argmax(np.abs(sub),axis=1);ii=idx[j];lags=np.where(ii<=MAXLAG,ii,ii-X.shape[1]).astype(np.int16);sgn=np.sign(sub[np.arange(X.shape[0]),j]).astype(np.int8);sgn[sgn==0]=1
    A=np.empty_like(W)
    for c in range(W.shape[0]):A[c]=np.roll(W[c],-int(lags[c]))*int(sgn[c])
    # Actually serialize timing/polarity side information and verify it.
    lb=Z.compress(lags.astype('<i2').tobytes());sb=Z.compress(np.packbits((sgn<0).astype(np.uint8),bitorder='little').tobytes())
    lr=np.frombuffer(D.decompress(lb),np.dtype('<i2'),count=W.shape[0]);neg=np.unpackbits(np.frombuffer(D.decompress(sb),np.uint8),bitorder='little',count=W.shape[0]).astype(bool);sr=np.where(neg,-1,1).astype(np.int8)
    if not np.array_equal(lr,lags) or not np.array_equal(sr,sgn):raise RuntimeError('sideinfo roundtrip')
    return np.ascontiguousarray(A),lags,sgn,len(lb)+len(sb)+64

def main(path):
    with segyio.open(path,'r',ignore_geometry=True) as f:
        f.mmap();ntr=f.tracecount;ns=len(f.samples);A=np.stack([np.asarray(f.trace[i],np.float32) for i in range(ntr)])
    std=float(A.std(dtype=np.float64));eps=.1*std;internal=eps*SAFETY
    cps=sorted(set([0,max(0,(ntr-SPACE)//2),max(0,ntr-SPACE)]));tps=sorted(set([0,3072,6144,9216,max(0,ns-TIME)]));rows=[]
    for c0 in cps:
      for t0 in tps:
        W=np.ascontiguousarray(A[c0:c0+SPACE,t0:min(ns,t0+TIME)]);AT=np.ascontiguousarray(W.T);sb,so,sme=sz3_best(AT,eps);lb,lme,lnz,lrep=lattice_tile(W,eps,internal);blob,pme,pd=encode_tile(W,internal);pb=len(blob)
        M,lags,sgn,side=align(W);mblob,mme,md=encode_tile(M,internal);mb=len(mblob)+side
        if not math.isfinite(mme) or mme>eps*(1+5e-6):raise RuntimeError(('moving hard',mme,eps,c0,t0))
        # Alignment/inverse alignment is only signed circular permutation, so L-inf error is invariant.
        rows.append({'c0':c0,'t0':t0,'shape':list(W.shape),'sz3_bytes':sb,'lattice_bytes':lb,'spectral_bytes':pb,'comoving_bytes':mb,'sideinfo_bytes':side,'gains':{'lattice':sb/lb,'spectral':sb/pb,'comoving':sb/mb},'bps':{'sz3':8*sb/W.size,'lattice':8*lb/W.size,'spectral':8*pb/W.size,'comoving':8*mb/W.size},'lattice_transition_nonzero':lnz,'spectral_correction_nonzero':pd['correction_nonzero_fraction'],'comoving_correction_nonzero':md['correction_nonzero_fraction'],'lag_min':int(lags.min()),'lag_median':float(np.median(lags)),'lag_max':int(lags.max()),'negative_polarity_fraction':float(np.mean(sgn<0)),'maxerr_aligned':mme})
    S=sum(r['sz3_bytes'] for r in rows);samples=sum(np.prod(r['shape']) for r in rows);agg=[]
    for name in ('lattice','spectral','comoving'):
      b=sum(r[name+'_bytes'] for r in rows);agg.append({'method':name,'bytes':b,'sz3_bytes':S,'gain_vs_sz3':S/b,'bps':8*b/samples,'min_tile_gain':min(r['gains'][name] for r in rows),'median_tile_gain':float(np.median([r['gains'][name] for r in rows])),'max_tile_gain':max(r['gains'][name] for r in rows)})
    # Three-language oracle with fully charged 2-bit selector and 8-byte length per tile; all component payloads independently self-decode.
    choices=[]
    for r in rows:
      vals=[('lattice',r['lattice_bytes']),('spectral',r['spectral_bytes']),('comoving',r['comoving_bytes'])];choices.append(min(vals,key=lambda x:x[1]))
    sel=np.array([{'lattice':0,'spectral':1,'comoving':2}[x[0]] for x in choices],np.uint8);packed=np.packbits(np.stack([(sel>>1)&1,sel&1],axis=1).ravel(),bitorder='little');selb=Z.compress(packed.tobytes());payload=sum(x[1] for x in choices);total=payload+len(selb)+8*len(rows)+128
    agg.append({'method':'adaptive3','bytes':total,'sz3_bytes':S,'gain_vs_sz3':S/total,'bps':8*total/samples,'selector_bytes':len(selb),'directory_bytes':8*len(rows),'counts':{k:sum(x[0]==k for x in choices) for k in ('lattice','spectral','comoving')}})
    agg.sort(key=lambda x:x['bytes']);out={'shape':[ntr,ns],'std':std,'eps':eps,'maxlag':MAXLAG,'channel_positions':cps,'time_positions':tps,'aggregate':agg,'rows':rows,'scope':'Comoving-wave diagnostic. Each channel is circularly delay-aligned and polarity-normalized to the decoder-known center trace before the existing self-decoding spectral/certified-correction grammar. Per-channel int16 delays and polarity bits are actually compressed/decoded and fully charged. Signed circular shifts preserve the hard L-inf error exactly when inverted. Includes an explicitly charged 3-language selector screen. Full-array integration only if this beats the existing spectral language on active shaker phases.'};print(json.dumps(out,indent=2),flush=True);json.dump(out,open('garner_comoving_wave_fastgate.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
