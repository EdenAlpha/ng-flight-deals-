import json,sys
import h5py,numpy as np,zstandard as zstd
from pysz import sz,szConfig,szErrorBoundMode

C=128;T=1024;SAFETY=1-1e-5;PHASES=4
Z=zstd.ZstdCompressor(level=19)

def stats(d):
    s=ss=0.;n=0
    for i in range(0,d.shape[0],2048):
        x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
    m=s/n;return m,float(np.sqrt(max(0,ss/n-m*m)))

def szrun(x,eps):
    best=None
    for tr in (False,True):
        a=np.ascontiguousarray((x.T if tr else x).astype(np.float32));cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
        b,_=sz.compress(a,cfg);r,_=sz.decompress(b,np.float32,a.shape);me=float(np.max(np.abs(a-r)))
        if me>eps*(1+5e-6):raise RuntimeError(('sz',me,eps))
        if best is None or int(b.size)<best:best=int(b.size)
    return best

def encode_int(a):
    a=np.asarray(a);mn=int(a.min()) if a.size else 0;mx=int(a.max()) if a.size else 0;c=[]
    for dt in (np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4')):
        if mn>=np.iinfo(dt).min and mx<=np.iinfo(dt).max:c.append((len(Z.compress(np.ascontiguousarray(a).astype(dt).tobytes()))+24,'signed_'+dt.str));break
    zz=((a.astype(np.int64)<<1)^(a.astype(np.int64)>>63)).astype(np.uint64);mz=int(zz.max()) if zz.size else 0
    for dt in (np.dtype('u1'),np.dtype('<u2'),np.dtype('<u4')):
        if mz<=np.iinfo(dt).max:c.append((len(Z.compress(np.ascontiguousarray(zz).astype(dt).tobytes()))+24,'zigzag_'+dt.str));break
    nz=a!=0;sup=Z.compress(np.packbits(nz.astype(np.uint8),bitorder='little').tobytes());v=a[nz];vmn=int(v.min()) if v.size else 0;vmx=int(v.max()) if v.size else 0
    for dt in (np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4')):
        if vmn>=np.iinfo(dt).min and vmx<=np.iinfo(dt).max:c.append((len(sup)+len(Z.compress(np.ascontiguousarray(v).astype(dt).tobytes()))+48,'sparse_'+dt.str));break
    return min(c)

def rep2(a):
    c=[]
    def add(name,x):b,r=encode_int(x);c.append((b+16,name+'_'+r))
    add('raw',a);dt=a.copy();dt[:,1:]-=a[:,:-1];add('dt',dt);ds=a.copy();ds[1:]-=a[:-1];add('ds',ds);L=a.copy();L[1:,1:]=a[1:,1:]-a[:-1,1:]-a[1:,:-1]+a[:-1,:-1];add('lorenzo',L)
    return min(c)

def quant_controls(ZX,mask,bound,phase):
    h=2*bound;phi=h*phase/PHASES;q=np.rint((ZX[mask]-phi)/h).astype(np.int32);r=phi+h*q
    if float(np.max(np.abs(ZX[mask]-r)))>bound*(1+1e-9):raise RuntimeError('control hard error')
    return q,r,h,phi

def checker(X,bound,phase,demod,tw):
    s=np.ones(T,np.float64) if not demod else np.where(np.arange(T)%2==0,1.0,-1.0);ZX=X*s[None,:]
    cc=np.arange(C)[:,None];tt=np.arange(T)[None,:];mask=((cc+tt)&1)==0
    q,rv,h,phi=quant_controls(ZX,mask,bound,phase);P=np.zeros_like(ZX);P[mask]=rv
    miss=np.argwhere(~mask)
    for c,t in miss:
        sv=[];tv=[]
        if c>0:sv.append(P[c-1,t])
        if c+1<C:sv.append(P[c+1,t])
        if t>0:tv.append(P[c,t-1])
        if t+1<T:tv.append(P[c,t+1])
        ss=sum(sv)/len(sv) if sv else 0.0;ttv=sum(tv)/len(tv) if tv else 0.0
        if sv and tv:P[c,t]=(ss+tw*ttv)/(1+tw)
        elif sv:P[c,t]=ss
        else:P[c,t]=ttv
    K=np.rint((ZX[~mask]-P[~mask])/(2*bound)).astype(np.int32);P[~mask]+=2*bound*K;R=P*s[None,:]
    # preserve 2-D structure by coding the two checkerboard control sublattices separately
    A0=np.rint((ZX[0::2,0::2]-phi)/h).astype(np.int32);A1=np.rint((ZX[1::2,1::2]-phi)/h).astype(np.int32);a0=rep2(A0);a1=rep2(A1);kr=encode_int(K);total=a0[0]+a1[0]+kr[0]+128
    return {'mesh':'checker','demod_nyquist':demod,'temporal_weight':tw,'phase':phase,'bytes':total,'control_bytes':a0[0]+a1[0],'control_reps':[a0[1],a1[1]],'correction_bytes':kr[0],'correction_rep':kr[1],'control_fraction':0.5,'correction_nonzero_fraction':float(np.mean(K!=0)),'maxerr':float(np.max(np.abs(X-R)))}

def grid2(X,bound,phase,demod):
    s=np.ones(T,np.float64) if not demod else np.where(np.arange(T)%2==0,1.0,-1.0);ZX=X*s[None,:];h=2*bound;phi=h*phase/PHASES
    qc=np.rint((ZX[0::2,0::2]-phi)/h).astype(np.int32);CV=phi+h*qc
    if float(np.max(np.abs(ZX[0::2,0::2]-CV)))>bound*(1+1e-9):raise RuntimeError('grid control hard error')
    P=np.empty_like(ZX)
    for c in range(C):
        c0=(c//2)*2;c1=min(C-2,c0+2);wc=0.0 if c1==c0 else (c-c0)/(c1-c0)
        ic0=c0//2;ic1=c1//2
        for t in range(T):
            t0=(t//2)*2;t1=min(T-2,t0+2);wt=0.0 if t1==t0 else (t-t0)/(t1-t0);it0=t0//2;it1=t1//2
            v00=CV[ic0,it0];v10=CV[ic1,it0];v01=CV[ic0,it1];v11=CV[ic1,it1]
            P[c,t]=(1-wc)*(1-wt)*v00+wc*(1-wt)*v10+(1-wc)*wt*v01+wc*wt*v11
    mask=np.zeros((C,T),bool);mask[0::2,0::2]=True;K=np.rint((ZX[~mask]-P[~mask])/(2*bound)).astype(np.int32);P[~mask]+=2*bound*K;R=P*s[None,:];ar=rep2(qc);kr=encode_int(K);total=ar[0]+kr[0]+112
    return {'mesh':'grid2x2','demod_nyquist':demod,'temporal_weight':None,'phase':phase,'bytes':total,'control_bytes':ar[0],'control_reps':[ar[1]],'correction_bytes':kr[0],'correction_rep':kr[1],'control_fraction':0.25,'correction_nonzero_fraction':float(np.mean(K!=0)),'maxerr':float(np.max(np.abs(X-R)))}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=stats(d);eps=.1*std;bound=eps*SAFETY;specs=[('early',0,3392),('center',14488,3392),('edge',14488,6784),('late',28976,3392)];rows=[];tiles=[]
        for name,t0,c0 in specs:
            X=np.asarray(d[t0:t0+T,c0:c0+C],np.float64).T;sb=szrun(X,eps);tiles.append({'tile':name,'sz3':sb})
            for ph in range(PHASES):
                for demod in (False,True):
                    for tw in (0.0,0.25,0.5,1.0,2.0,4.0):
                        r=checker(X,bound,ph,demod,tw)
                        if r['maxerr']>eps*(1+5e-6):raise RuntimeError(('hard checker',name,r['maxerr'],eps))
                        r.update({'tile':name,'direct_sz3_bytes':sb,'gain_vs_sz3':sb/r['bytes'],'bps':8*r['bytes']/X.size});rows.append(r)
                    r=grid2(X,bound,ph,demod)
                    if r['maxerr']>eps*(1+5e-6):raise RuntimeError(('hard grid',name,r['maxerr'],eps))
                    r.update({'tile':name,'direct_sz3_bytes':sb,'gain_vs_sz3':sb/r['bytes'],'bps':8*r['bytes']/X.size});rows.append(r)
        defs=sorted(set((r['mesh'],r['demod_nyquist'],r['temporal_weight'],r['phase']) for r in rows),key=str);s=sum(t['sz3'] for t in tiles);combos=[]
        for key in defs:
            rr=[r for r in rows if (r['mesh'],r['demod_nyquist'],r['temporal_weight'],r['phase'])==key];b=sum(r['bytes'] for r in rr)
            combos.append({'mesh':key[0],'demod_nyquist':key[1],'temporal_weight':key[2],'phase':key[3],'bytes':b,'sz3_bytes':s,'gain_vs_sz3':s/b,'bps':8*b/(C*T*len(rr)),'min_tile_gain':min(r['gain_vs_sz3'] for r in rr),'control_fraction':rr[0]['control_fraction'],'control_bytes':sum(r['control_bytes'] for r in rr),'correction_bytes':sum(r['correction_bytes'] for r in rr),'median_correction_nonzero':float(np.median([r['correction_nonzero_fraction'] for r in rr]))})
        combos.sort(key=lambda r:r['bytes']);out={'std':std,'eps':eps,'combos':combos,'rows':rows,'scope':'2-D control-mesh screen. Checkerboard transmits exactly half the samples but every missing sample is decoder-derived from up to four spatial/temporal controls; optional (-1)^t demodulation turns negative lag-1 into positive control geometry. Aggressive 2x2 grid transmits one quarter. Controls use coarse 2eps legal lattice, all correction bytes counted, final hard error verified, one definition frozen across four tiles.'}
        print(json.dumps({'best':combos[:12]},indent=2),flush=True);json.dump(out,open('imperial_spacetime_control_mesh.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
