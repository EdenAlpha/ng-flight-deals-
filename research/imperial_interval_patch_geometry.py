import json,sys,math
import h5py,numpy as np,zstandard as zstd
from pysz import sz,szConfig,szErrorBoundMode

C=128;T=1024;SAFETY=1-2e-4
SPECS=(('early',0,3392),('center',14488,3392),('edge',14488,6784),('late',28976,3392))
MINS=((2,8),(4,16),(8,16))
Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor()

def stats(d):
    s=ss=0.;n=0
    for i in range(0,d.shape[0],2048):
        x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
    m=s/n;return m,float(np.sqrt(max(0,ss/n-m*m)))

def szrun(X,eps):
    best=None
    for tr in (False,True):
        A=np.ascontiguousarray((X.T if tr else X).astype(np.float32));cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
        b,_=sz.compress(A,cfg);R,_=sz.decompress(b,np.float32,A.shape);me=float(np.max(np.abs(A-R)))
        if me>eps*(1+5e-6):raise RuntimeError(('sz',me,eps))
        if best is None or int(b.size)<best:best=int(b.size)
    return best

def coords(nc,nt):
    c=np.linspace(-1.0,1.0,nc,dtype=np.float64)[:,None];t=np.linspace(-1.0,1.0,nt,dtype=np.float64)[None,:]
    return np.broadcast_to(c,(nc,nt)),np.broadcast_to(t,(nc,nt))

def fit_patch(X,bound,kind):
    nc,nt=X.shape;cc,tt=coords(nc,nt);cols=[np.ones(X.size),cc.ravel(),tt.ravel()]
    if kind=='bilinear':cols.append((cc*tt).ravel())
    A=np.stack(cols,axis=1);th=np.linalg.lstsq(A,X.ravel(),rcond=None)[0].astype(np.float32)
    return th,float(np.max(np.abs(X-eval_patch(th,nc,nt,kind))))

def eval_patch(th,nc,nt,kind):
    cc,tt=coords(nc,nt);P=np.float64(th[0])+np.float64(th[1])*cc+np.float64(th[2])*tt
    if kind=='bilinear':P=P+np.float64(th[3])*cc*tt
    return P

def encode_int(a):
    a=np.asarray(a,np.int32);c=[];mn=int(a.min()) if a.size else 0;mx=int(a.max()) if a.size else 0
    for dt in (np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4')):
        if mn>=np.iinfo(dt).min and mx<=np.iinfo(dt).max:
            b=Z.compress(a.astype(dt).tobytes());c.append((len(b),dt.str,'signed',b));break
    zz=((a.astype(np.int64)<<1)^(a.astype(np.int64)>>63)).astype(np.uint64);mz=int(zz.max()) if zz.size else 0
    for dt in (np.dtype('u1'),np.dtype('<u2'),np.dtype('<u4')):
        if mz<=np.iinfo(dt).max:
            b=Z.compress(zz.astype(dt).tobytes());c.append((len(b),dt.str,'zigzag',b));break
    return min(c,key=lambda z:z[0])

class Encoder:
    def __init__(self,X,bound,minc,mint):
        self.X=X;self.bound=bound;self.minc=minc;self.mint=mint;self.status=[];self.aff=[];self.bil=[];self.raw=[]
    def rec(self,c0,c1,t0,t1):
        B=self.X[c0:c1,t0:t1];nc,nt=B.shape
        for code,kind in ((1,'affine'),(2,'bilinear')):
            th,me=fit_patch(B,self.bound,kind)
            if me<=self.bound:
                self.status.append(code);(self.aff if code==1 else self.bil).append(th);return
        if nc<=self.minc and nt<=self.mint:
            self.status.append(3);self.raw.append((c0,c1,t0,t1));return
        self.status.append(0);cm=(c0+c1)//2;tm=(t0+t1)//2
        if nc>self.minc and nt>self.mint:parts=((c0,cm,t0,tm),(c0,cm,tm,t1),(cm,c1,t0,tm),(cm,c1,tm,t1))
        elif nc>self.minc:parts=((c0,cm,t0,t1),(cm,c1,t0,t1))
        else:parts=((c0,c1,t0,tm),(c0,c1,tm,t1))
        for p in parts:self.rec(*p)
    def run(self):self.rec(0,self.X.shape[0],0,self.X.shape[1]);return self

def decode_tree(shape,status,aff,bil,rawq,bound,minc,mint,demod):
    R=np.empty(shape,np.float64);si=ai=bi=ri=0
    def rec(c0,c1,t0,t1):
        nonlocal si,ai,bi,ri
        code=int(status[si]);si+=1;nc=c1-c0;nt=t1-t0
        if code==1:
            R[c0:c1,t0:t1]=eval_patch(aff[ai],nc,nt,'affine');ai+=1;return
        if code==2:
            R[c0:c1,t0:t1]=eval_patch(bil[bi],nc,nt,'bilinear');bi+=1;return
        if code==3:
            n=nc*nt;R[c0:c1,t0:t1]=rawq[ri:ri+n].reshape(nc,nt)*(2*bound);ri+=n;return
        cm=(c0+c1)//2;tm=(t0+t1)//2
        if nc>minc and nt>mint:parts=((c0,cm,t0,tm),(c0,cm,tm,t1),(cm,c1,t0,tm),(cm,c1,tm,t1))
        elif nc>minc:parts=((c0,cm,t0,t1),(cm,c1,t0,t1))
        else:parts=((c0,c1,t0,tm),(c0,c1,tm,t1))
        for p in parts:rec(*p)
    rec(0,shape[0],0,shape[1])
    if si!=len(status) or ai!=len(aff) or bi!=len(bil) or ri!=len(rawq):raise RuntimeError(('decode accounting',si,ai,bi,ri,len(status),len(aff),len(bil),len(rawq)))
    if demod:R*=np.where(np.arange(shape[1])%2==0,1.0,-1.0)[None,:]
    return R

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=stats(d);eps=.1*std;bound=eps*SAFETY;rows=[];tiles=[]
        for name,t0,c0 in SPECS:
            X0=np.asarray(d[t0:t0+T,c0:c0+C],np.float64).T;direct=szrun(X0,eps);tiles.append({'tile':name,'sz3':direct})
            for demod in (False,True):
                sign=np.where(np.arange(T)%2==0,1.0,-1.0)[None,:] if demod else 1.0;X=X0*sign
                for minc,mint in MINS:
                    e=Encoder(X,bound,minc,mint).run();qparts=[]
                    for a,b,c,d2 in e.raw:qparts.append(np.rint(X[a:b,c:d2]/(2*bound)).astype(np.int32).ravel())
                    q=np.concatenate(qparts) if qparts else np.empty(0,np.int32);qr=encode_int(q)
                    status=np.asarray(e.status,np.uint8);bits=np.stack([(status>>1)&1,status&1],axis=1).ravel().astype(np.uint8);st=Z.compress(np.packbits(bits,bitorder='little').tobytes())
                    aff=np.asarray(e.aff,np.float32).reshape(-1,3) if e.aff else np.empty((0,3),np.float32);bil=np.asarray(e.bil,np.float32).reshape(-1,4) if e.bil else np.empty((0,4),np.float32)
                    ab=Z.compress(aff.tobytes());bb=Z.compress(bil.tobytes())
                    if qr[2]=='signed':rraw=np.frombuffer(D.decompress(qr[3]),dtype=np.dtype(qr[1])).astype(np.int32)
                    else:
                        zz=np.frombuffer(D.decompress(qr[3]),dtype=np.dtype(qr[1])).astype(np.uint64);rraw=((zz>>1).astype(np.int64)^-(zz&1).astype(np.int64)).astype(np.int32)
                    R=decode_tree(X.shape,status,aff,bil,rraw,bound,minc,mint,demod);me=float(np.max(np.abs(X0-R)))
                    if not math.isfinite(me) or me>eps*(1+5e-6):raise RuntimeError(('hard',name,demod,minc,mint,me,eps))
                    total=len(st)+len(ab)+len(bb)+qr[0]+160;cnt={str(k):int(np.sum(status==k)) for k in range(4)}
                    rows.append({'tile':name,'demod_nyquist':demod,'min_patch':[minc,mint],'bytes':total,'sz3_bytes':direct,'gain_vs_sz3':direct/total,'bps':8*total/X.size,'maxerr':me,'node_count':len(status),'status_counts':cnt,'topology_bytes':len(st),'affine_bytes':len(ab),'bilinear_bytes':len(bb),'fallback_bytes':qr[0],'fallback_samples':int(q.size),'fallback_fraction':q.size/X.size})
        combos=[];ss=sum(t['sz3'] for t in tiles)
        for demod in (False,True):
            for minp in MINS:
                rr=[r for r in rows if r['demod_nyquist']==demod and r['min_patch']==list(minp)];b=sum(r['bytes'] for r in rr)
                combos.append({'demod_nyquist':demod,'min_patch':list(minp),'bytes':b,'sz3_bytes':ss,'gain_vs_sz3':ss/b,'bps':8*b/(C*T*len(rr)),'min_tile_gain':min(r['gain_vs_sz3'] for r in rr),'fallback_fraction':sum(r['fallback_samples'] for r in rr)/(C*T*len(rr)),'topology_bytes':sum(r['topology_bytes'] for r in rr),'affine_bytes':sum(r['affine_bytes'] for r in rr),'bilinear_bytes':sum(r['bilinear_bytes'] for r in rr),'fallback_bytes':sum(r['fallback_bytes'] for r in rr)})
        combos.sort(key=lambda r:r['bytes']);out={'std':std,'eps':eps,'bound':bound,'combos':combos,'rows':rows,'scope':'Self-decoding interval-patch geometry codec. A whole 2-D space-time node is replaced by one affine or bilinear surface only when the transmitted float32 surface lies inside every sample hard-error interval. Otherwise the node recursively splits; minimum leaves fall back to exact legal 2eps lattice states. Quadtree topology, model coefficients and fallback states are all compressed and counted. Optional deterministic (-1)^t demodulation. Four frozen tiles, fixed definition aggregate, no AI.'}
        print(json.dumps({'best':combos[:6]},indent=2),flush=True);json.dump(out,open('imperial_interval_patch_geometry.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
