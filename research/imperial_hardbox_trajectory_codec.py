import json,sys,struct,math
import h5py,numpy as np,zstandard as zstd
import imperial_decoder_phase_automaton as m

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
C=128;NT=8192
SCALES=(64,256,1024,4096)
BASE={
 'hard':{'ar32_bytes':661373,'sz3_bytes':754436},
 'easy':{'ar32_bytes':237943,'sz3_bytes':282633},
 'medium':{'ar32_bytes':416391,'sz3_bytes':460273},
 'far':{'ar32_bytes':551268,'sz3_bytes':636418},
}
ZC=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()
DTS=(np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4'),np.dtype('<i8'),np.dtype('u1'),np.dtype('<u2'),np.dtype('<u4'),np.dtype('<u8'))
DTID={d.str:i for i,d in enumerate(DTS)}


def _sdtype(a):
 a=np.asarray(a,np.int64);mn=int(a.min()) if a.size else 0;mx=int(a.max()) if a.size else 0
 for d in DTS[:4]:
  q=np.iinfo(d)
  if mn>=q.min and mx<=q.max:return d
 return DTS[3]

def _udtype(a):
 a=np.asarray(a,np.uint64);mx=int(a.max()) if a.size else 0
 for d in DTS[4:]:
  if mx<=np.iinfo(d).max:return d
 return DTS[-1]

def _zz(a):
 a=np.asarray(a,np.int64);return ((a<<1)^(a>>63)).astype(np.uint64)

def _unzz(u):
 u=np.asarray(u,np.uint64);return ((u>>1).astype(np.int64)^-(u&1).astype(np.int64))

def _make_frame(a,tid):
 a=np.asarray(a,np.int64).ravel()
 if tid==0:b=a;dt=_sdtype(b)
 elif tid==1:
  b=a.copy()
  if b.size>1:b[1:]-=a[:-1]
  dt=_sdtype(b)
 elif tid==2:b=_zz(a);dt=_udtype(b)
 elif tid==3:
  d=a.copy()
  if d.size>1:d[1:]-=a[:-1]
  b=_zz(d);dt=_udtype(b)
 else:raise ValueError(tid)
 raw=np.ascontiguousarray(b.astype(dt)).tobytes();z=ZC.compress(raw)
 head=struct.pack('<4sBBII',b'TRJ1',tid,DTID[dt.str],a.size,len(z))
 return head+z

def _decode_frame(buf):
 magic,tid,did,n,L=struct.unpack_from('<4sBBII',buf,0)
 if magic!=b'TRJ1' or 14+L!=len(buf):raise RuntimeError('frame header')
 dt=DTS[did];raw=ZD.decompress(buf[14:]);b=np.frombuffer(raw,dtype=dt,count=n)
 if b.size!=n:raise RuntimeError('frame count')
 if tid==0:a=b.astype(np.int64)
 elif tid==1:a=np.cumsum(b.astype(np.int64),dtype=np.int64)
 elif tid==2:a=_unzz(b.astype(np.uint64))
 elif tid==3:a=np.cumsum(_unzz(b.astype(np.uint64)),dtype=np.int64)
 else:raise RuntimeError('frame transform')
 return a

def frame(a):
 a=np.asarray(a,np.int64).ravel();c=[_make_frame(a,t) for t in range(4)];best=min(c,key=len);d=_decode_frame(best)
 if not np.array_equal(d,a):raise RuntimeError('frame replay')
 return best

def legal_intervals(x,eps):
 lo=np.ceil(np.asarray(x,np.float64)-eps).astype(np.int64)
 hi=np.floor(np.asarray(x,np.float64)+eps).astype(np.int64)
 if np.any(lo>hi):raise RuntimeError('empty integer box')
 return lo,hi

def clipi(x,lo,hi):return int(max(int(lo),min(int(hi),int(x))))

def const_segments(x,eps):
 lo,hi=legal_intervals(x,eps);n=len(x);lens=[];vals=[];s=0;prev=0
 while s<n:
  L=int(lo[s]);U=int(hi[s]);e=s+1
  while e<n:
   nL=max(L,int(lo[e]));nU=min(U,int(hi[e]))
   if nL>nU:break
   L,U=nL,nU;e+=1
  target=prev if vals else int(np.rint(x[s]));v=clipi(target,L,U)
  lens.append(e-s);vals.append(v);prev=v;s=e
 return np.asarray(lens,np.int64),np.asarray(vals,np.int64)

def ceildiv(a,b):return -((-int(a))//int(b))

def linear_segments(x,eps,S):
 lo,hi=legal_intervals(x,eps);n=len(x);lens=[];anchors=[];slopes=[];s=0;prev_q=0;prev_a=0;prev_len=0
 while s<n:
  pred=int(np.rint(prev_a+prev_q*prev_len/float(S))) if lens else int(np.rint(x[s]))
  cand=[clipi(pred,lo[s],hi[s]),clipi(int(np.rint(x[s])),lo[s],hi[s]),int(lo[s]),int(hi[s]),int((int(lo[s])+int(hi[s]))//2)]
  cand=list(dict.fromkeys(cand));best=None
  for a in cand:
   qlo=-(1<<62);qhi=(1<<62);e=s+1
   while e<n:
    d=e-s
    nqlo=max(qlo,ceildiv((int(lo[e])-a)*S,d))
    nqhi=min(qhi,((int(hi[e])-a)*S)//d)
    if nqlo>nqhi:break
    qlo,qhi=nqlo,nqhi;e+=1
   if e==s+1:q=prev_q
   else:q=max(qlo,min(qhi,prev_q))
   key=(e-s,-abs(q-prev_q),-abs(a-pred))
   if best is None or key>best[0]:best=(key,e,a,int(q))
  _,e,a,q=best
  lens.append(e-s);anchors.append(a);slopes.append(q);prev_a=a;prev_q=q;prev_len=e-s;s=e
 return np.asarray(lens,np.int64),np.asarray(anchors,np.int64),np.asarray(slopes,np.int64)

def const_stream(X,eps):
 counts=[];lens=[];first=[];dv=[]
 for c in range(X.shape[0]):
  L,V=const_segments(X[c],eps);counts.append(len(L));lens.extend(L.tolist());first.append(int(V[0]))
  if len(V)>1:dv.extend(np.diff(V).tolist())
 fs=[frame(counts),frame(lens),frame(first),frame(dv)];stream=struct.pack('<4sBIII',b'CTR1',0,X.shape[0],X.shape[1],len(fs))+b''.join(struct.pack('<I',len(q))+q for q in fs)
 off=17;arr=[]
 for _ in range(4):L=struct.unpack_from('<I',stream,off)[0];off+=4;arr.append(_decode_frame(stream[off:off+L]));off+=L
 if off!=len(stream):raise RuntimeError('const trailing')
 dc,dl,df,dd=arr;R=np.empty(X.shape,np.float64);li=di=0
 for c in range(X.shape[0]):
  ns=int(dc[c]);v=int(df[c]);t=0
  for j in range(ns):
   n=int(dl[li]);li+=1
   if j>0:v+=int(dd[di]);di+=1
   R[c,t:t+n]=v;t+=n
  if t!=X.shape[1]:raise RuntimeError(('const length',c,t))
 if li!=len(dl) or di!=len(dd):raise RuntimeError('const parse')
 me=float(np.max(np.abs(X-R)))
 if me>eps*(1+1e-12):raise RuntimeError(('const hard',me,eps))
 return {'kind':'constant','bytes':len(stream),'bps':8*len(stream)/X.size,'maxerr':me,'segments':int(len(lens)),'mean_segment_len':float(X.size/len(lens)),'median_segments_per_channel':float(np.median(counts))}

def linear_stream(X,eps,S):
 counts=[];lens=[];first_a=[];first_q=[];da=[];dq=[]
 for c in range(X.shape[0]):
  L,A,Q=linear_segments(X[c],eps,S);counts.append(len(L));lens.extend(L.tolist());first_a.append(int(A[0]));first_q.append(int(Q[0]))
  for j in range(1,len(L)):
   pred=int(np.rint(float(A[j-1])+float(Q[j-1])*float(L[j-1])/float(S)))
   da.append(int(A[j])-pred);dq.append(int(Q[j])-int(Q[j-1]))
 fs=[frame(counts),frame(lens),frame(first_a),frame(first_q),frame(da),frame(dq)]
 stream=struct.pack('<4sBIIII',b'LTR1',1,X.shape[0],X.shape[1],S,len(fs))+b''.join(struct.pack('<I',len(q))+q for q in fs)
 off=21;arr=[]
 for _ in range(6):L=struct.unpack_from('<I',stream,off)[0];off+=4;arr.append(_decode_frame(stream[off:off+L]));off+=L
 if off!=len(stream):raise RuntimeError('linear trailing')
 dc,dl,dfa,dfq,dda,ddq=arr;R=np.empty(X.shape,np.float64);li=di=0
 for c in range(X.shape[0]):
  ns=int(dc[c]);a=int(dfa[c]);q=int(dfq[c]);t=0;prevn=0
  for j in range(ns):
   n=int(dl[li]);li+=1
   if j>0:
    pred=int(np.rint(float(a)+float(q)*float(prevn)/float(S)));a=pred+int(dda[di]);q=q+int(ddq[di]);di+=1
   d=np.arange(n,dtype=np.float64);R[c,t:t+n]=float(a)+(float(q)/float(S))*d;t+=n;prevn=n
  if t!=X.shape[1]:raise RuntimeError(('linear length',S,c,t))
 if li!=len(dl) or di!=len(dda) or di!=len(ddq):raise RuntimeError('linear parse')
 me=float(np.max(np.abs(X-R)))
 if me>eps*(1+1e-10):raise RuntimeError(('linear hard',S,me,eps))
 return {'kind':'linear','scale':S,'bytes':len(stream),'bps':8*len(stream)/X.size,'maxerr':me,'segments':int(len(lens)),'mean_segment_len':float(X.size/len(lens)),'median_segments_per_channel':float(np.median(counts))}

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
  for region,c0 in SPECS:
   X=np.asarray(d[:NT,c0:c0+C],np.float64).T;rr=[const_stream(X,eps)]
   for S in SCALES:rr.append(linear_stream(X,eps,S))
   for r in rr:
    r.update({'region':region,'c0':c0,'ar32_bytes':BASE[region]['ar32_bytes'],'sz3_bytes':BASE[region]['sz3_bytes'],'gain_vs_ar32':BASE[region]['ar32_bytes']/r['bytes'],'gain_vs_sz3':BASE[region]['sz3_bytes']/r['bytes']})
    print(json.dumps(r),flush=True)
   best=min(rr,key=lambda x:x['bytes']);rows.append({'region':region,'best':best,'all':rr})
  out={'global_std':gstd,'eps':eps,'shape':[C,NT],'scales':list(SCALES),'controls':'Pinned exact PR420 run 31788514939 on identical canonical 128x8192 regions and global epsilon; trajectory candidates independently decode/replay and hard-error validate.','rows':rows,'scope':'Hard-box-native trajectory simplification. Constant mode greedily emits the longest run whose integer reconstruction interval intersection remains nonempty, then serializes only per-channel segment counts, lengths and value changes. Linear mode emits piecewise fixed-point lines: a small deterministic anchor candidate set is tested at each segment start; for each anchor the exact integer slope interval satisfying every following source hard box is intersected until empty, and the longest legal segment is selected. First anchors/slopes and subsequent continuation residuals/slope deltas are fully serialized. Every metadata vector is materialized as a framed Zstd stream selected from exact raw/delta/zigzag/delta-zigzag representations, byte-decoded, and used to reconstruct every sample before unchanged max-error validation. No predictor residual, oracle rate, hidden model or post-hoc repair.'}
  json.dump(out,open('imperial_hardbox_trajectory_codec.json','w'),indent=2)
  print(json.dumps({'summary':[{'region':x['region'],'best_kind':x['best']['kind'],'scale':x['best'].get('scale'),'bytes':x['best']['bytes'],'bps':x['best']['bps'],'gain_ar32':x['best']['gain_vs_ar32'],'gain_sz3':x['best']['gain_vs_sz3'],'mean_segment_len':x['best']['mean_segment_len']} for x in rows]},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])