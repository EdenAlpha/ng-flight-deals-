import json,sys,math
import h5py,numpy as np,zstandard as zstd
from pysz import sz,szConfig,szErrorBoundMode

C=128;T=1024;SAFETY=1-1e-5;Z=zstd.ZstdCompressor(level=19)

def stats(d):
    s=ss=0.;n=0
    for i in range(0,d.shape[0],2048):
        x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
    m=s/n;return m,float(np.sqrt(max(0,ss/n-m*m)))

def szround(a,eps):
    best=None
    for tr in (False,True):
        A=np.ascontiguousarray((a.T if tr else a).astype(np.float32));cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
        b,_=sz.compress(A,cfg);R,_=sz.decompress(b,np.float32,A.shape);me=float(np.max(np.abs(A-R)))
        if me>eps*(1+5e-6):raise RuntimeError(('sz error',me,eps))
        if tr:R=R.T
        row=(int(b.size),R.astype(np.float64),me,'T' if tr else 'C')
        if best is None or row[0]<best[0]:best=row
    return best

def anchor_positions(kind,n=C):
    if kind.startswith('stride'):
        s=int(kind[6:]);p=list(range(0,n,s))
    elif kind=='2of5':p=[i for i in range(n) if i%5 in (0,2)]
    elif kind=='2of5_shift':p=[i for i in range(n) if i%5 in (0,3)]
    else:raise ValueError(kind)
    if 0 not in p:p=[0]+p
    if n-1 not in p:p.append(n-1)
    return np.asarray(sorted(set(p)),np.int32)

def predict(decoded,pos,mode):
    P=np.empty((C,T),np.float64);P[pos]=decoded
    aset=set(map(int,pos.tolist()))
    for c in range(C):
        if c in aset:continue
        j=int(np.searchsorted(pos,c));l=int(pos[j-1]);r=int(pos[j]);a=(c-l)/(r-l)
        if mode=='linear':P[c]=(1-a)*P[l]+a*P[r]
        elif mode=='nearest':P[c]=P[l] if a<0.5 else P[r]
        else:raise ValueError(mode)
    return P

def encode_k(k):
    k=np.asarray(k,np.int32).ravel();cands=[];mn=int(k.min()) if k.size else 0;mx=int(k.max()) if k.size else 0
    for dt in (np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4')):
        if mn>=np.iinfo(dt).min and mx<=np.iinfo(dt).max:
            cands.append((len(Z.compress(k.astype(dt).tobytes()))+24,'signed_'+dt.str));break
    zz=((k.astype(np.int64)<<1)^(k.astype(np.int64)>>63)).astype(np.uint64);mz=int(zz.max()) if zz.size else 0
    for dt in (np.dtype('u1'),np.dtype('<u2'),np.dtype('<u4')):
        if mz<=np.iinfo(dt).max:
            cands.append((len(Z.compress(zz.astype(dt).tobytes()))+24,'zigzag_'+dt.str));break
    nz=k!=0;sup=Z.compress(np.packbits(nz.astype(np.uint8),bitorder='little').tobytes());v=k[nz]
    vmn=int(v.min()) if v.size else 0;vmx=int(v.max()) if v.size else 0
    for dt in (np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4')):
        if vmn>=np.iinfo(dt).min and vmx<=np.iinfo(dt).max:
            vb=Z.compress(v.astype(dt).tobytes());cands.append((len(sup)+len(vb)+48,'sparse_'+dt.str));break
    return min(cands),float(np.mean(nz)),float(np.mean(np.abs(k)==1))

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=stats(d);eps=.1*std;internal=eps*SAFETY;step=2*internal
        specs=[('early',0,3392),('center',14488,3392),('edge',14488,6784),('late',28976,3392)]
        kinds=('stride2','2of5','2of5_shift','stride3','stride4','stride5');modes=('linear','nearest');rows=[];szmap={}
        for name,t0,c0 in specs:
            X=np.asarray(d[t0:t0+T,c0:c0+C],np.float64).T;raw=X.size*2;direct=szround(X,eps)[0];szmap[name]=direct
            for kind in kinds:
                pos=anchor_positions(kind);ab,Adec,ame,aori=szround(X[pos],eps);mask=np.ones(C,bool);mask[pos]=False
                for mode in modes:
                    P=predict(Adec,pos,mode);K=np.rint((X[mask]-P[mask])/step).astype(np.int32);corr,nzf,a1=encode_k(K);R=P.copy();R[mask]=P[mask]+step*K;R[pos]=Adec
                    me=float(np.max(np.abs(X-R)))
                    if me>eps*(1+5e-6):raise RuntimeError(('hard error',name,kind,mode,me,eps))
                    total=ab+corr[0]+64
                    rows.append({'tile':name,'pattern':kind,'interp':mode,'anchors':int(len(pos)),'anchor_fraction':len(pos)/C,'anchor_sz3_bytes':ab,'anchor_orientation':aori,'anchor_maxerr':ame,'correction_bytes':corr[0],'correction_rep':corr[1],'correction_nonzero_fraction':nzf,'correction_abs1_fraction':a1,'total_bytes':total,'direct_sz3_bytes':direct,'gain_vs_direct_sz3':direct/total,'ratio_raw':raw/total,'bps':8*total/X.size,'direct_sz3_bps':8*direct/X.size,'maxerr':me})
        combos=[]
        for kind in kinds:
            for mode in modes:
                rr=[r for r in rows if r['pattern']==kind and r['interp']==mode];b=sum(r['total_bytes'] for r in rr);s=sum(szmap[r['tile']] for r in rr)
                combos.append({'pattern':kind,'interp':mode,'bytes':b,'direct_sz3_bytes':s,'gain_vs_sz3':s/b,'bps':8*b/(C*T*len(rr)),'min_tile_gain':min(r['gain_vs_direct_sz3'] for r in rr),'median_correction_nonzero':float(np.median([r['correction_nonzero_fraction'] for r in rr])),'anchor_fraction':rr[0]['anchor_fraction']})
        combos.sort(key=lambda r:r['bytes']);out={'std':std,'eps':eps,'gauge_length_m':10.0,'channel_interval_m':4.0,'gauge_over_channel_interval':2.5,'combos':combos,'rows':rows,'scope':'Gauge-aware spatial decimation codec screen. Anchor channels are actually SZ3-compressed and decoded; omitted channels are predicted only from those decoded anchors, then exact lattice corrections are serialized and fully charged. Four precommitted tiles, fixed pattern/interpolation aggregate, unchanged hard max-error.'}
        print(json.dumps({'best':combos[:8]},indent=2),flush=True);json.dump(out,open('imperial_gauge_aware_spatial_decimation.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
