import json,os,struct,sys
import numpy as np,segyio,zstandard as zstd
src=open('research/soda_grid_sparse.py').read().split('\npath=sys.argv[1]')[0]
exec(compile(src,'soda_grid_sparse.py','exec'),globals())

MAG=b'STRNv001';HDR='<8sBBBBBB4I5Q';HS=struct.calcsize(HDR)

def shifted(x,d):
    if d==0:return x
    y=np.zeros_like(x)
    if d>0:y[d:]=x[:-d]
    else:y[:d]=x[-d:]
    return y

def build_residual(M,maxshift,predmask):
    C,L,S,T=M.shape;R=np.empty_like(M);modes=np.zeros((C,L,S),np.uint8);ns=2*maxshift+1
    raw_ones=0;res_ones=0;use=[0,0,0,0]
    shifts=range(-maxshift,maxshift+1)
    for c in range(C):
      for l in range(L):
       for s in range(S):
        cur=M[c,l,s];best=int(np.count_nonzero(cur));bestcode=0;bestpred=None
        # code groups: station, line, component
        if (predmask&1) and s>0:
          p0=M[c,l,s-1]
          for d in shifts:
            p=shifted(p0,d);sc=int(np.count_nonzero(np.logical_xor(cur,p)))
            if sc<best:best,bestcode,bestpred=sc,1+(d+maxshift),p
        if (predmask&2) and l>0:
          p0=M[c,l-1,s]
          for d in shifts:
            p=shifted(p0,d);sc=int(np.count_nonzero(np.logical_xor(cur,p)))
            if sc<best:best,bestcode,bestpred=sc,1+ns+(d+maxshift),p
        if (predmask&4) and c>0:
          p0=M[c-1,l,s]
          for d in shifts:
            p=shifted(p0,d);sc=int(np.count_nonzero(np.logical_xor(cur,p)))
            if sc<best:best,bestcode,bestpred=sc,1+2*ns+(d+maxshift),p
        R[c,l,s]=cur if bestcode==0 else np.logical_xor(cur,bestpred);modes[c,l,s]=bestcode
        raw_ones+=int(np.count_nonzero(cur));res_ones+=best;use[0 if bestcode==0 else 1+(bestcode-1)//ns]+=1
    return R,modes,{'raw_support_ones':raw_ones,'residual_support_ones':res_ones,'residual_fraction_of_raw':res_ones/max(raw_ones,1),'mode_use':use}

def recover_mask(R,modes,maxshift):
    C,L,S,T=R.shape;M=np.empty_like(R);ns=2*maxshift+1
    for c in range(C):
      for l in range(L):
       for s in range(S):
        code=int(modes[c,l,s]);rr=R[c,l,s]
        if code==0:M[c,l,s]=rr;continue
        z=code-1;grp=z//ns;d=(z%ns)-maxshift
        if grp==0:p0=M[c,l,s-1]
        elif grp==1:p0=M[c,l-1,s]
        elif grp==2:p0=M[c-1,l,s]
        else:raise RuntimeError('mode group')
        M[c,l,s]=np.logical_xor(rr,shifted(p0,d))
    return M

def encode(K,maxshift,predmask,perm,valmode,level):
    zc=zstd.ZstdCompressor(level=level);M=K!=0;R,modes,stats=build_residual(M,maxshift,predmask);pc=int(perm[0]|(perm[1]<<2)|(perm[2]<<4)|(perm[3]<<6));RP=np.transpose(R,perm);modeb=zc.compress(modes.tobytes());resb=zc.compress(np.packbits(RP.ravel(),bitorder='little').tobytes());P=np.transpose(K,perm);MP=np.transpose(M,perm);vals=P[MP].astype(np.int32)
    v1=v2=v3=b'';dc=1
    if valmode==0:
      dc=dtype_code(vals);v1=zc.compress(vals.astype(DT[dc],copy=False).tobytes())
    else:
      sign=vals<0;ab=np.abs(vals);exc=ab!=1;v1=zc.compress(np.packbits(sign,bitorder='little').tobytes());v2=zc.compress(np.packbits(exc,bitorder='little').tobytes());mag=(ab[exc]-2).astype(np.int32);dc=dtype_code(mag);v3=zc.compress(mag.astype(DT[dc],copy=False).tobytes()) if mag.size else b''
    h=struct.pack(HDR,MAG,1,maxshift,predmask,pc,valmode,dc,*K.shape,len(modeb),len(resb),len(v1),len(v2),len(v3));parts={'mode':len(modeb),'support_residual':len(resb),'v1':len(v1),'v2':len(v2),'v3':len(v3),**stats};return h+modeb+resb+v1+v2+v3,parts

def decode(blob):
    q=struct.unpack(HDR,blob[:HS]);magic,ver,maxshift,predmask,pc,valmode,dc,d0,d1,d2,d3,lmode,lres,l1,l2,l3=q
    if magic!=MAG or ver!=1:raise RuntimeError('header')
    p=HS;modeb=blob[p:p+lmode];p+=lmode;resb=blob[p:p+lres];p+=lres;v1=blob[p:p+l1];p+=l1;v2=blob[p:p+l2];p+=l2;v3=blob[p:p+l3];p+=l3
    shape=(d0,d1,d2,d3);perm=tuple((pc>>(2*i))&3 for i in range(4));pshape=tuple(shape[i] for i in perm);n=int(np.prod(shape));zd=zstd.ZstdDecompressor();modes=np.frombuffer(zd.decompress(modeb),np.uint8,count=d0*d1*d2).reshape(d0,d1,d2);RP=np.unpackbits(np.frombuffer(zd.decompress(resb),np.uint8),bitorder='little',count=n).reshape(pshape).astype(bool);invp=np.argsort(perm);R=np.transpose(RP,invp);M=recover_mask(R,modes,maxshift);MP=np.transpose(M,perm);ne=int(MP.sum())
    if valmode==0:vals=np.frombuffer(zd.decompress(v1),dtype=DT[dc],count=ne).astype(np.int32)
    else:
      sign=np.unpackbits(np.frombuffer(zd.decompress(v1),np.uint8),bitorder='little',count=ne).astype(bool);exc=np.unpackbits(np.frombuffer(zd.decompress(v2),np.uint8),bitorder='little',count=ne).astype(bool);ab=np.ones(ne,np.int32)
      if exc.any():ab[exc]=np.frombuffer(zd.decompress(v3),dtype=DT[dc],count=int(exc.sum())).astype(np.int32)+2
      vals=np.where(sign,-ab,ab)
    P=np.zeros(pshape,np.int32);P[MP]=vals;return np.transpose(P,invp)

path=sys.argv[1]
with segyio.open(path,'r',ignore_geometry=True) as f:X=np.asarray(f.trace.raw[:],np.float32).copy();gx=np.asarray(f.attributes(segyio.TraceField.GroupX)[:],np.int64);gy=np.asarray(f.attributes(segyio.TraceField.GroupY)[:],np.int64)
eps=.1*float(X.astype(np.float64).std());step=2*eps;raw=X.nbytes;G,tm,outids,geom=geometry_map(X,gx,gy)
for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
O=np.rint(X[outids]/step).astype(np.int32);K=delta(G,3)
perms=[(1,2,0,3),(1,0,2,3),(2,1,0,3),(2,0,1,3),(3,1,2,0)];rows=[]
for maxshift in [0,2,4,8]:
 for pm in [1,3,7]:
  # build once for statistics, encode() rebuilds but keeps code straightforward/auditable
  for perm in perms:
   for vm in [0,1]:
    for level in [19,22]:
      b,parts=encode(K,maxshift,pm,perm,vm,level);R=decode(b)
      if not np.array_equal(R,K):raise RuntimeError('transport decode mismatch')
      rows.append({'maxshift':maxshift,'predictors':pm,'perm':list(perm),'value_mode':'signed' if vm==0 else 'signmag','level':level,'bytes':len(b),'parts':parts})
rows.sort(key=lambda r:r['bytes'])
# Reuse best outlier representation from existing codec search.
outrows=[]
for td in [0,1]:
 A=delta(O,1) if td else O
 for level in [19,22]:
  for perm in [(0,1,2,3),(3,1,2,0)]:
   for rep in [0,1,2]:
    b=encode_out_sparse(A,perm,rep,level);RR=decode_out_sparse(b);RR=undelta(RR,1) if td else RR
    if not np.array_equal(RR,O):raise RuntimeError('out decode')
    outrows.append({'tdiff':bool(td),'level':level,'perm':list(perm),'rep':['raw','sparse','ternary'][rep],'bytes':len(b)})
outrows.sort(key=lambda r:r['bytes']);br=rows[0];bo=outrows[0];vm=0 if br['value_mode']=='signed' else 1;mb,_=encode(K,br['maxshift'],br['predictors'],tuple(br['perm']),vm,br['level']);OA=delta(O,1) if bo['tdiff'] else O;repid={'raw':0,'sparse':1,'ternary':2}[bo['rep']];ob=encode_out_sparse(OA,tuple(bo['perm']),repid,bo['level']);top=struct.pack('<8sdQQ',b'STRTOP01',eps,len(mb),len(ob))+mb+ob
p=struct.calcsize('<8sdQQ');_,ee,lm,lo=struct.unpack('<8sdQQ',top[:p]);RK=decode(top[p:p+lm]);ROA=decode_out_sparse(top[p+lm:p+lm+lo]);RG=undelta(RK,3);RO=undelta(ROA,1) if bo['tdiff'] else ROA;Y=np.empty_like(X)
for tid,c,l,s in tm:Y[tid]=RG[c,l,s].astype(np.float32)*np.float32(2*ee)
Y[outids]=RO.astype(np.float32)*np.float32(2*ee);me=float(np.max(np.abs(X-Y)));szb,sze=sz3_bytes(X,eps);ratio=raw/len(top);szr=raw/szb
out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'eps':eps,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'main_candidates':rows[:20],'outlier_candidates':outrows[:12],'container_bytes':len(top),'ratio':ratio,'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'sz3':{'bytes':szb,'ratio':szr,'maxerr':sze},'gain_over_sz3':ratio/szr}
print(json.dumps(out,indent=2),flush=True);json.dump(out,open('soda_support_transport.json','w'),indent=2)
