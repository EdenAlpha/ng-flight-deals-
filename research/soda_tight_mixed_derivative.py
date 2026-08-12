import json,os,struct,sys
import numpy as np

# Reuse the exact PR #170 loader, geometry, outlier codec, public epsilon
# contract, and frozen run codec. This experiment changes only the lossless
# representation of the already-legal integer reconstruction state grid.
src=open('research/soda_frozen_eps_sweep.py').read().split('\ndef main(path,frac):')[0]
exec(compile(src,'soda_frozen_eps_sweep.py','exec'),globals())

DMAG=b'MDRV0001'
DHDR='<8sBBBB4I4B4Q'
DHS=struct.calcsize(DHDR)
DTYPE={1:np.dtype('<i1'),2:np.dtype('<i2'),3:np.dtype('<i4')}
# Only the established strongest fast backends are screened here. Method IDs
# are the existing PR #161 IDs: raw=0, zstd22=1, brotli11=3.
SCREEN_METHODS=(0,1,3)


def dtype_code(a):
    if a.size==0:return 1
    lo=int(a.min());hi=int(a.max())
    return 1 if lo>=-128 and hi<=127 else (2 if lo>=-32768 and hi<=32767 else 3)


def best_fast(raw):
    rows=[]
    for m in SCREEN_METHODS:
        b=comp_one(raw,m)
        if decomp_one(b,m)!=raw:raise RuntimeError(('backend roundtrip',m))
        rows.append((len(b),m,b))
    rows.sort(key=lambda x:(x[0],x[1]));return rows[0],[(METHOD_NAMES[m],n) for n,m,_ in rows]


def delta_axis(A,axis):
    R=np.array(A,dtype=np.int32,copy=True)
    a=[slice(None)]*A.ndim;b=[slice(None)]*A.ndim
    a[axis]=slice(1,None);b[axis]=slice(None,-1)
    R[tuple(a)]=A[tuple(a)]-A[tuple(b)]
    return R


def undelta_axis(A,axis):
    return np.cumsum(A,axis=axis,dtype=np.int64).astype(np.int32)


def transform(Q,mask):
    R=np.asarray(Q,np.int32)
    if mask&1:R=delta_axis(R,1) # acquisition line
    if mask&2:R=delta_axis(R,2) # station
    if mask&4:R=delta_axis(R,3) # time
    return R


def untransform(R,mask):
    Q=np.asarray(R,np.int32)
    if mask&4:Q=undelta_axis(Q,3)
    if mask&2:Q=undelta_axis(Q,2)
    if mask&1:Q=undelta_axis(Q,1)
    return Q


def pack2(codes):
    c=np.asarray(codes,np.uint8).ravel();pad=(-c.size)%4
    if pad:c=np.concatenate([c,np.zeros(pad,np.uint8)])
    q=c.reshape(-1,4)
    return (q[:,0]|(q[:,1]<<2)|(q[:,2]<<4)|(q[:,3]<<6)).astype(np.uint8).tobytes()


def unpack2(buf,n):
    b=np.frombuffer(buf,np.uint8);c=np.empty(b.size*4,np.uint8)
    c[0::4]=b&3;c[1::4]=(b>>2)&3;c[2::4]=(b>>4)&3;c[3::4]=(b>>6)&3
    return c[:n]


def choose_frame(raw):
    (n,m,b),allrows=best_fast(raw);return m,b,allrows


def encode_residual(R,mask,rep):
    flat=np.ascontiguousarray(R,dtype=np.int32).ravel();n=flat.size
    frames=[b'',b'',b'',b''];methods=[0,0,0,0];choices=[];dc=1
    if rep==0: # dense minimal signed integers
        dc=dtype_code(flat);raw=flat.astype(DTYPE[dc],copy=False).tobytes();methods[0],frames[0],rows=choose_frame(raw);choices.append(rows)
    elif rep==1: # sparse bitmap + exact signed nonzero values
        nz=flat!=0;vals=flat[nz];dc=dtype_code(vals);raw0=np.packbits(nz,bitorder='little').tobytes();raw1=vals.astype(DTYPE[dc],copy=False).tobytes()
        methods[0],frames[0],r0=choose_frame(raw0);methods[1],frames[1],r1=choose_frame(raw1);choices.extend([r0,r1])
    elif rep==2: # 2-bit 0/+1/-1/exception alphabet + exact exception values
        codes=np.full(n,3,np.uint8);codes[flat==0]=0;codes[flat==1]=1;codes[flat==-1]=2;exc=(codes==3);vals=flat[exc];dc=dtype_code(vals)
        raw0=pack2(codes);raw1=vals.astype(DTYPE[dc],copy=False).tobytes();methods[0],frames[0],r0=choose_frame(raw0);methods[1],frames[1],r1=choose_frame(raw1);choices.extend([r0,r1])
    elif rep==3: # support/sign/exception bitplanes + positive exception magnitude
        nz=flat!=0;vals=flat[nz];sign=vals<0;ab=np.abs(vals);exc=ab!=1;mags=(ab[exc]-2).astype(np.int32);dc=dtype_code(mags)
        raws=[np.packbits(nz,bitorder='little').tobytes(),np.packbits(sign,bitorder='little').tobytes(),np.packbits(exc,bitorder='little').tobytes(),mags.astype(DTYPE[dc],copy=False).tobytes()]
        for i,raw in enumerate(raws):methods[i],frames[i],rr=choose_frame(raw);choices.append(rr)
    else:raise ValueError(rep)
    h=struct.pack(DHDR,DMAG,1,int(mask),int(rep),int(dc),*R.shape,*methods,*[len(x) for x in frames])
    diag={'mask':int(mask),'rep':int(rep),'dtype_code':int(dc),'methods':[METHOD_NAMES[m] for m in methods],'frame_bytes':[len(x) for x in frames],'header_bytes':DHS,'backend_candidates':choices,'nonzero_fraction':float(np.mean(flat!=0)),'min':int(flat.min()),'max':int(flat.max())}
    return h+b''.join(frames),diag


def decode_residual(blob):
    q=struct.unpack(DHDR,blob[:DHS]);magic,ver,mask,rep,dc,C,L,S,T,*rest=q
    if magic!=DMAG or ver!=1:raise RuntimeError('mixed derivative header')
    methods=rest[:4];lens=rest[4:];p=DHS;frames=[]
    for ln in lens:frames.append(blob[p:p+ln]);p+=ln
    if p!=len(blob):raise RuntimeError('mixed derivative length')
    raw=[decomp_one(frames[i],methods[i]) for i in range(4)];shape=(C,L,S,T);n=int(np.prod(shape))
    if rep==0:
        flat=np.frombuffer(raw[0],dtype=DTYPE[dc],count=n).astype(np.int32)
    elif rep==1:
        nz=np.unpackbits(np.frombuffer(raw[0],np.uint8),bitorder='little',count=n).astype(bool);nv=int(nz.sum());vals=np.frombuffer(raw[1],dtype=DTYPE[dc],count=nv).astype(np.int32);flat=np.zeros(n,np.int32);flat[nz]=vals
    elif rep==2:
        codes=unpack2(raw[0],n);exc=codes==3;ne=int(exc.sum());vals=np.frombuffer(raw[1],dtype=DTYPE[dc],count=ne).astype(np.int32);flat=np.zeros(n,np.int32);flat[codes==1]=1;flat[codes==2]=-1;flat[exc]=vals
    elif rep==3:
        nz=np.unpackbits(np.frombuffer(raw[0],np.uint8),bitorder='little',count=n).astype(bool);nv=int(nz.sum());sign=np.unpackbits(np.frombuffer(raw[1],np.uint8),bitorder='little',count=nv).astype(bool);exc=np.unpackbits(np.frombuffer(raw[2],np.uint8),bitorder='little',count=nv).astype(bool);ne=int(exc.sum());mags=np.frombuffer(raw[3],dtype=DTYPE[dc],count=ne).astype(np.int32);ab=np.ones(nv,np.int32);ab[exc]=mags+2;vals=np.where(sign,-ab,ab);flat=np.zeros(n,np.int32);flat[nz]=vals
    else:raise RuntimeError('bad mixed derivative rep')
    return untransform(flat.reshape(shape),int(mask))


def main(path,frac):
    X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());public_eps=float(frac)*std;internal_eps=public_eps*INTERNAL_SAFETY;step=2*internal_eps;raw=int(X.nbytes)
    G0,tm,outids,geom=geometry_map(X,gx,gy);Q=np.asarray(G0,np.int32)
    for tid,c,l,s in tm:Q[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    O=np.rint(X[outids]/step).astype(np.int32);bo=best_out(O);RO=decode_out_best(bo,O.shape)
    if not np.array_equal(RO,O):raise RuntimeError('outlier decode')
    # Frozen PR170 run codec is the incumbent and is counted as a candidate.
    K=delta(Q,3);run_blob,run_parts=encode_main_fixed(K);RK=decode_main(run_blob)
    if not np.array_equal(RK,K):raise RuntimeError('incumbent decode')
    candidates=[{'kind':'frozen_run','bytes':len(run_blob),'blob':run_blob,'parts':run_parts}]
    # Tight-fidelity screen: time delta alone and exact mixed derivatives with
    # station and/or line. No model, matching map, or learned parameter exists.
    for mask in (4,5,6,7):
        R=transform(Q,mask)
        for rep in range(4):
            b,d=encode_residual(R,mask,rep);RQ=decode_residual(b)
            if not np.array_equal(RQ,Q):raise RuntimeError(('mixed exact decode',mask,rep))
            candidates.append({'kind':'mixed_derivative','bytes':len(b),'blob':b,'diag':d})
    candidates.sort(key=lambda r:r['bytes']);best=candidates[0]
    if best['kind']=='frozen_run':BQ=undelta(decode_main(best['blob']),3)
    else:BQ=decode_residual(best['blob'])
    Y=np.empty_like(X)
    for tid,c,l,s in tm:Y[tid]=BQ[c,l,s].astype(np.float32)*np.float32(step)
    Y[outids]=RO.astype(np.float32)*np.float32(step);me=float(np.max(np.abs(X-Y)));container=TOPS+int(best['bytes'])+int(bo[0]);szb,sze=sz3_bytes(X,public_eps)
    summary=[]
    for r in candidates[:12]:summary.append({k:v for k,v in r.items() if k!='blob' and k!='parts'})
    out={'file':os.path.basename(path),'shape':list(X.shape),'std':std,'epsilon_fraction_of_std':float(frac),'public_eps':public_eps,'internal_eps':internal_eps,'raw_bytes':raw,'geometry':geom,'Q_time_delta_nonzero_fraction':float(np.mean(K!=0)),'incumbent_main_bytes':len(run_blob),'incumbent_container_bytes':TOPS+len(run_blob)+int(bo[0]),'best_kind':best['kind'],'best_main_bytes':int(best['bytes']),'best_detail':{k:v for k,v in best.items() if k not in ('blob','parts')},'top_candidates':summary,'outlier_bytes':int(bo[0]),'container_bytes':container,'ratio':float(raw/container),'maxerr':me,'valid':bool(me<=public_eps*(1+3e-6)),'sz3':{'bytes':int(szb),'ratio':float(raw/szb),'maxerr':float(sze)},'gain_vs_direct_sz3':float(szb/container),'gain_vs_incumbent':float((TOPS+len(run_blob)+int(bo[0]))/container)}
    if not out['valid']:raise RuntimeError(('hard error',me,public_eps))
    print(json.dumps({k:out[k] for k in ('epsilon_fraction_of_std','best_kind','incumbent_container_bytes','container_bytes','ratio','gain_vs_direct_sz3','gain_vs_incumbent','maxerr')},indent=2),flush=True);json.dump(out,open('soda_tight_mixed_derivative.json','w'),indent=2)

main(sys.argv[1],float(sys.argv[2]))
