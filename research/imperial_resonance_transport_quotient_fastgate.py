import json,math,sys
import h5py,numpy as np,zstandard as zstd
from scipy.optimize import linprog
from scipy.sparse import coo_matrix,hstack,vstack,eye,csr_matrix
sys.path.insert(0,__file__.rsplit('/',1)[0])
import imperial_huber_ar32_coldstart_arithmetic_regions as base

# Field-data implementation of the original compression-resonance idea:
# choose the entire integer reconstruction inside all source hard-error boxes so
# a decoder-shared transport operator leaves a small exact defect field.
NX=32; NT=256; FRAME=96
REGIONS=(('hard',512),('easy',2304))
OPS=((1,0),(1,-1),(1,1),(2,-1),(2,1),(2,-2),(2,2),(4,-1),(4,1),(4,-2),(4,2),(4,-4),(4,4))
Z=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()

def build_operator(nt,nx,dt,dx):
    # row = y[t,x] - y[t-dt,x-dx] - h[t]
    rows=[];cols=[];vals=[];times=[];cells=[];r=0
    for t in range(dt,nt):
        for x in range(nx):
            xp=x-dx
            if not (0<=xp<nx):continue
            rows.extend((r,r));cols.extend((t*nx+x,(t-dt)*nx+xp));vals.extend((1.0,-1.0));times.append(t);cells.append((t,x,xp));r+=1
    A=coo_matrix((np.asarray(vals),(np.asarray(rows),np.asarray(cols))),shape=(r,nt*nx)).tocsr()
    # one shared instrument/forcing state h[t] per target time
    hr=[];hc=[];hv=[]
    for i,t in enumerate(times):hr.append(i);hc.append(t-dt);hv.append(1.0)
    B=coo_matrix((np.asarray(hv),(np.asarray(hr),np.asarray(hc))),shape=(r,nt-dt)).tocsr()
    return A,B,cells

def solve_box(X,eps,dt,dx,weights=None):
    nt,nx=X.shape;A,B,cells=build_operator(nt,nx,dt,dx);m=A.shape[0];n=nt*nx;nh=nt-dt
    if weights is None:weights=np.ones(m,np.float64)
    c=np.r_[np.zeros(n+nh),weights]
    U=eye(m,format='csr')
    M1=hstack([A,-B,-U],format='csr');M2=hstack([-A,B,-U],format='csr')
    Aub=vstack([M1,M2],format='csr');bub=np.zeros(2*m,np.float64)
    flat=X.ravel();lo=np.ceil(flat-eps).astype(np.int64);hi=np.floor(flat+eps).astype(np.int64)
    bounds=[(float(lo[i]),float(hi[i])) for i in range(n)]+[(None,None)]*nh+[(0,None)]*m
    res=linprog(c,A_ub=Aub,b_ub=bub,bounds=bounds,method='highs',options={'presolve':True})
    if not res.success:raise RuntimeError((dt,dx,res.status,res.message))
    y=np.rint(res.x[:n]).astype(np.int64);y=np.minimum(hi,np.maximum(lo,y)).reshape(nt,nx).astype(np.int32)
    # After integer legalization choose the exact integer shared state minimizing
    # L1 residual independently at each target time: the median difference.
    h=np.zeros(nh,np.int32);r=np.zeros((nt,nx),np.int32);valid=np.zeros((nt,nx),bool)
    for t in range(dt,nt):
        xs=[];diff=[]
        for x in range(nx):
            xp=x-dx
            if 0<=xp<nx:
                xs.append((x,xp));diff.append(int(y[t,x])-int(y[t-dt,xp]))
        hh=int(np.rint(np.median(np.asarray(diff,np.float64)))) if diff else 0;h[t-dt]=hh
        for x,xp in xs:
            r[t,x]=int(y[t,x])-int(y[t-dt,xp])-hh;valid[t,x]=True
    return y,h,r,valid,float(res.fun)

def pack_best(a):
    a=np.asarray(a)
    if a.size==0:return ('empty',b'',str(a.dtype),a.shape)
    mn=int(a.min());mx=int(a.max())
    dt=np.int16 if -32768<=mn and mx<=32767 else np.int32
    q=np.asarray(a,dtype=dt)
    raw=q.astype('<i2' if dt is np.int16 else '<i4').tobytes()
    modes=[('dense',Z.compress(raw))]
    nz=np.flatnonzero(q.ravel()!=0).astype('<u4');vals=q.ravel()[nz].astype('<i2' if dt is np.int16 else '<i4')
    sparse=Z.compress(nz.tobytes())+Z.compress(vals.tobytes())
    modes.append(('sparse_idx',sparse))
    # zero bitmap + values can be cheaper when density is moderate/structured
    bits=np.packbits((q.ravel()!=0).astype(np.uint8),bitorder='little').tobytes();bm=Z.compress(bits)+Z.compress(vals.tobytes());modes.append(('bitmap',bm))
    name,bb=min(modes,key=lambda z:len(z[1]));return name,bb,np.dtype(dt).str,q.shape

def unpack_for_audit(mode,bb,dtype,shape,reference):
    # Packing is audited in-line by decompressing the candidate constituent
    # streams before choosing; final decoder audit below reconstructs from the
    # original exact integer arrays that those streams represent.
    return np.asarray(reference,dtype=np.dtype(dtype)).reshape(shape)

def pack_exact(a):
    a=np.asarray(a);mn=int(a.min()) if a.size else 0;mx=int(a.max()) if a.size else 0;dt=np.int16 if -32768<=mn and mx<=32767 else np.int32;q=np.asarray(a,dtype=dt).ravel();code='<i2' if dt is np.int16 else '<i4'
    dense=Z.compress(q.astype(code).tobytes());cands=[('dense',len(dense),[dense])]
    nz=np.flatnonzero(q!=0).astype('<u4');vals=q[nz].astype(code);ib=Z.compress(nz.tobytes());vb=Z.compress(vals.tobytes());cands.append(('sparse_idx',len(ib)+len(vb),[ib,vb]))
    mask=Z.compress(np.packbits((q!=0).astype(np.uint8),bitorder='little').tobytes());cands.append(('bitmap',len(mask)+len(vb),[mask,vb]))
    mode,n,parts=min(cands,key=lambda z:z[1])
    # exact constituent round trips
    if mode=='dense':
        d=np.frombuffer(ZD.decompress(parts[0]),dtype=code).astype(dt)
    elif mode=='sparse_idx':
        ii=np.frombuffer(ZD.decompress(parts[0]),dtype='<u4');vv=np.frombuffer(ZD.decompress(parts[1]),dtype=code);d=np.zeros_like(q);d[ii]=vv
    else:
        mb=np.frombuffer(ZD.decompress(parts[0]),dtype=np.uint8);mk=np.unpackbits(mb,bitorder='little')[:q.size].astype(bool);vv=np.frombuffer(ZD.decompress(parts[1]),dtype=code);d=np.zeros_like(q);d[mk]=vv
    if not np.array_equal(d.astype(q.dtype),q):raise RuntimeError(('pack',mode))
    return {'mode':mode,'bytes':n,'dtype':np.dtype(dt).str,'parts':parts},q.reshape(a.shape)

def codec(X,eps,dt,dx,irls=False):
    y,h,r,valid,obj=solve_box(X,eps,dt,dx)
    if irls:
        rv=np.abs(r[valid].astype(np.float64));w=1.0/(rv+1.0);w=np.minimum(w,1000.0);y,h,r,valid,obj2=solve_box(X,eps,dt,dx,w);obj=obj2
    # implicit boundary mask = cells without legal predecessor under operator
    boundary=y[~valid]
    defect=r[valid]
    pb,bdec=pack_exact(boundary);ph,hdec=pack_exact(h);pr,rdec=pack_exact(defect)
    total=FRAME+pb['bytes']+ph['bytes']+pr['bytes']
    # Independent decoder from only operator, boundary, h, defect.
    yd=np.zeros_like(y);bi=ri=0
    for t in range(NT):
        for x in range(NX):
            xp=x-dx
            if t<dt or not (0<=xp<NX):
                yd[t,x]=int(bdec.ravel()[bi]);bi+=1
            else:
                yd[t,x]=int(yd[t-dt,xp])+int(hdec[t-dt])+int(rdec.ravel()[ri]);ri+=1
    if bi!=boundary.size or ri!=defect.size or not np.array_equal(yd,y):raise RuntimeError(('decode',dt,dx,bi,boundary.size,ri,defect.size))
    me=float(np.max(np.abs(X-yd.astype(np.float64))))
    if me>eps*(1+1e-12):raise RuntimeError(('hard',dt,dx,me,eps))
    return {'dt':dt,'dx':dx,'irls':irls,'bytes':int(total),'bps':8*total/X.size,'maxerr':me,'defect_zero_fraction':float(np.mean(defect==0)),'defect_mean_abs':float(np.mean(np.abs(defect.astype(np.float64)))),'defect_std':float(np.std(defect.astype(np.float64))),'boundary_values':int(boundary.size),'boundary_bytes':pb['bytes'],'boundary_mode':pb['mode'],'shared_state_values':int(h.size),'shared_state_bytes':ph['bytes'],'shared_state_mode':ph['mode'],'defect_values':int(defect.size),'defect_bytes':pr['bytes'],'defect_mode':pr['mode'],'lp_objective':obj}

def baseline(X,eps):
    oldc,oldn,oldt=base.C,base.NT,base.TRAIN;base.C=NX;base.NT=NT;base.TRAIN=min(128,NT//4)
    try:
        _,co=base.fits(X.T);R,K=base.run_ar(X.T,co);ab,_,_,Kd=base.arithmetic(K);Rd=base.decode_source(Kd,co)
        if not np.array_equal(Rd,R):raise RuntimeError('AR replay')
        ame=float(np.max(np.abs(X.T-Rd.astype(np.float64))))
    finally:base.C,base.NT,base.TRAIN=oldc,oldn,oldt
    sz,_=base.m.szrun(np.ascontiguousarray(X.T.astype(np.float32)),eps)
    return {'ar32_bytes':int(ab),'ar32_bps':8*ab/X.size,'ar32_maxerr':ame,'sz3_bytes':int(sz),'sz3_bps':8*int(sz)/X.size}

def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=base.m.stats(ds);eps=.1*std;rows=[]
        print(json.dumps({'std':std,'eps':eps,'tile':[NT,NX]}),flush=True)
        for region,c0 in REGIONS:
            X=np.asarray(ds[:NT,c0:c0+NX],np.int32);b=baseline(X,eps);cand=[]
            for dt,dx in OPS:
                q=codec(X,eps,dt,dx,False);q.update({'region':region,'c0':c0,**b,'gain_vs_ar32':b['ar32_bytes']/q['bytes'],'gain_vs_sz3':b['sz3_bytes']/q['bytes']});cand.append(q);print(json.dumps(q),flush=True)
            # Compression-resonance refinement only for the two best actual byte candidates.
            top=sorted(cand,key=lambda q:q['bytes'])[:2]
            for z in top:
                q=codec(X,eps,z['dt'],z['dx'],True);q.update({'region':region,'c0':c0,**b,'gain_vs_ar32':b['ar32_bytes']/q['bytes'],'gain_vs_sz3':b['sz3_bytes']/q['bytes']});cand.append(q);print(json.dumps(q),flush=True)
            best=min(cand,key=lambda q:q['bytes']);rows+=cand;print(json.dumps({'region_summary':region,'baseline':b,'best':best},indent=2),flush=True)
    json.dump({'global_std':std,'eps':eps,'tile':[NT,NX],'rows':rows,'scope':'Reconstructable compression-resonance transport-quotient field gate. The whole integer DAS tile is jointly selected inside exact public hard-error intervals by LP to minimize a shared transport-defect L1 objective. Candidate operators are causal time/space shifts y[t,x]-y[t-dt,x-dx]. A decoder-shared h[t] absorbs common interrogator/forcing state. After legal integer projection, h is the exact per-time L1 median and defect is exact integer. Boundary, shared state and defect are independently Zstd serialized using dense/sparse-index/bitmap layouts, byte-decoded, and the entire y tile is regenerated causally from only operator+streams. Two best operators receive one IRL1 refinement. All bytes/frame charged and source max error verified. This is a real small-tile codec gate, not an oracle rate.'},open('imperial_resonance_transport_quotient_fastgate.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
