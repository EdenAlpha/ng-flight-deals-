import heapq,json,math,sys
import h5py,numpy as np,zstandard as zstd
import imperial_decoder_phase_automaton as m

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
C=128;NT=8192;TB=1024;TRAIN=1024;P=32;STEP=267;AR_MODEL_BYTES=177
Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor()

def fit_ar(X):
 rows=[];ys=[]
 for c in range(C):
  x=np.asarray(X[c,:TRAIN],np.float64)
  for t in range(P,TRAIN):rows.append(np.r_[1.0,x[t-P:t][::-1]]);ys.append(x[t])
 return np.linalg.lstsq(np.asarray(rows,np.float64),np.asarray(ys,np.float64),rcond=None)[0].astype(np.float32)

def run_ar(X,ar):
 R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);a=float(ar[0]);b=np.asarray(ar[1:],np.float32)
 for c in range(C):
  for t in range(X.shape[1]):
   p=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
   k=int(np.rint((float(X[c,t])-p)/STEP));K[c,t]=k;R[c,t]=p+STEP*k
 return R,K

def optimal_partition(x,eps):
 counts=np.bincount((np.asarray(x,np.int16).astype(np.int32)+32768).ravel(),minlength=65536)
 vals=np.flatnonzero(counts).astype(np.int32)-32768;c=counts[counts>0].astype(np.int64);nval=len(vals)
 pref=np.zeros(nval+1,np.int64);pref[1:]=np.cumsum(c);dp=np.full(nval+1,-np.inf,np.float64);prev=np.full(nval+1,-1,np.int32);dp[0]=0.0;width=2.0*float(eps)
 for end in range(nval):
  lo=int(np.searchsorted(vals,vals[end]-width-1e-12,side='left'));starts=np.arange(lo,end+1,dtype=np.int32);n=(pref[end+1]-pref[starts]).astype(np.float64);score=dp[starts]+n*np.log2(n);j=int(np.argmax(score));dp[end+1]=score[j];prev[end+1]=int(starts[j])
 groups=[];e=nval
 while e>0:
  s=int(prev[e]);groups.append((int(vals[s]),int(vals[e-1]),int(pref[e]-pref[s])));e=s
 groups.reverse();return groups

def huff_lengths(counts):
 n=len(counts)
 if n==1:return np.zeros(1,np.uint8)
 heap=[];uid=0
 for s,w in enumerate(counts):heap.append((int(w),uid,s));uid+=1
 heapq.heapify(heap);children={}
 while len(heap)>1:
  wa,ia,a=heapq.heappop(heap);wb,ib,b=heapq.heappop(heap);node=('n',uid);uid+=1;children[node]=(a,b);heapq.heappush(heap,(wa+wb,uid,node));uid+=1
 root=heap[0][2];L=np.zeros(n,np.uint8);stack=[(root,0)]
 while stack:
  node,d=stack.pop()
  if isinstance(node,int):L[node]=d
  else:
   a,b=children[node];stack.append((a,d+1));stack.append((b,d+1))
 return L

def canonical(lengths):
 pairs=sorted((int(l),s) for s,l in enumerate(lengths) if int(l)>0);codes={};code=0;prev=0
 for l,s in pairs:
  code <<= l-prev;codes[s]=(code,l);code+=1;prev=l
 return codes

def pack_syms(ids,codes):
 if not codes:return b''
 out=bytearray();acc=0;nb=0
 for s in np.asarray(ids,np.int32).ravel():
  code,l=codes[int(s)];acc=(acc<<l)|code;nb+=l
  while nb>=8:
   nb-=8;out.append((acc>>nb)&255);acc &= (1<<nb)-1 if nb else 0
 if nb:out.append((acc<<(8-nb))&255)
 return bytes(out)

def decode_syms(payload,lengths,n):
 if len(lengths)==1:return np.zeros(n,np.int32)
 codes=canonical(lengths);rev={(l,c):s for s,(c,l) in codes.items()};out=np.empty(n,np.int32);j=0;code=0;l=0
 for byte in payload:
  for sh in range(7,-1,-1):
   code=(code<<1)|((byte>>sh)&1);l+=1
   s=rev.get((l,code))
   if s is not None:
    out[j]=s;j+=1
    if j==n:return out
    code=0;l=0
 raise RuntimeError(('huffman short decode',j,n))

def encode_tile(X,eps):
 groups=optimal_partition(X,eps);his=np.asarray([g[1] for g in groups],np.int32);centers2=np.asarray([g[0]+g[1] for g in groups],np.int32);counts=np.asarray([g[2] for g in groups],np.int64)
 ids=np.searchsorted(his,np.asarray(X,np.int32).ravel(),side='left').astype(np.int32);lengths=huff_lengths(counts);codes=canonical(lengths);raw=pack_syms(ids,codes);comp=Z.compress(raw)
 use_z=len(comp)+1<len(raw)+1;payload=(b'Z'+comp) if use_z else (b'R'+raw)
 modelraw=centers2.astype('<i4').tobytes()+lengths.astype('u1').tobytes();model=Z.compress(modelraw);total=len(model)+len(payload)+40
 mr=D.decompress(model);G=len(groups);c2=np.frombuffer(mr[:4*G],'<i4',count=G).astype(np.int32);ld=np.frombuffer(mr[4*G:4*G+G],np.uint8,count=G)
 pd=D.decompress(payload[1:]) if payload[:1]==b'Z' else payload[1:];idd=decode_syms(pd,ld,X.size);Rd=(c2[idd].astype(np.float64)*0.5).reshape(X.shape);me=float(np.max(np.abs(np.asarray(X,np.float64)-Rd)))
 if me>eps*(1+1e-12):raise RuntimeError(('hardbox huffman hard',me,eps))
 if not np.array_equal(idd,ids):raise RuntimeError('id decode')
 return {'bytes':total,'bps':8*total/X.size,'groups':G,'model_bytes':len(model)+24,'payload_bytes':len(payload)+16,'huffman_raw_bytes':len(raw),'payload_zstd':bool(use_z),'maxerr':me,'mean_code_length':float(np.sum(counts*lengths)/np.sum(counts))}

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
  for region,c0 in SPECS:
   X=np.asarray(d[:NT,c0:c0+C],np.int16).T;ar=fit_ar(X.astype(np.float64));R,K=run_ar(X.astype(np.float64),ar);me=float(np.max(np.abs(X.astype(np.float64)-R.astype(np.float64))))
   if me>eps*(1+1e-12):raise RuntimeError((region,'AR hard',me,eps))
   arbytes=AR_MODEL_BYTES;artiles=[];scalar=[];sz=0
   for t0 in range(0,NT,TB):
    A=K[:,t0:t0+TB];n,rep,Kd=m.encode_k(A)
    if not np.array_equal(A,Kd):raise RuntimeError('AR K decode')
    arbytes+=n;artiles.append({'t0':t0,'bytes':n,'rep':rep})
    S=X[:,t0:t0+TB];q=encode_tile(S,eps);q['t0']=t0;scalar.append(q)
    b,_=m.szrun(S.astype(np.float64),eps);sz+=b
   sb=sum(x['bytes'] for x in scalar);row={'region':region,'c0':c0,'samples':int(X.size),'ar32':{'bytes':arbytes,'bps':8*arbytes/X.size,'gain_vs_sz3':sz/arbytes,'maxerr':me,'tiles':artiles},'local_hardbox_huffman':{'bytes':sb,'bps':8*sb/X.size,'gain_vs_sz3':sz/sb,'gain_vs_ar32':arbytes/sb,'tiles':scalar},'sz3_bytes':sz,'sz3_bps':8*sz/X.size,'winner':'scalar' if sb<arbytes else 'ar32','winner_bytes':min(sb,arbytes),'winner_gain_vs_sz3':sz/min(sb,arbytes)}
   rows.append(row);print(json.dumps(row,indent=2),flush=True)
 out={'global_std':gstd,'eps':eps,'tile_shape':[C,TB],'rows':rows,'scope':'Constructive real-byte follow-up to PR #219. Every 128x1024 source tile gets the exact target-adaptive entropy-minimizing scalar hard-box partition under the unchanged epsilon. Because the target-adaptive model is not free, the decoder receives a compressed table of half-integer reconstruction centers plus canonical Huffman code lengths; the symbol stream is actually Huffman packed, optionally Zstd-compressed only when smaller, byte-decoded back to exact symbol IDs, reconstructed, and hard-error verified. All model/payload/tile framing bytes are charged. Persistent AR32 step267 and matched SZ3 are rerun on the same complete 128x8192 regions. This tests whether the strong easy-tile scalar oracle observed in PR #219 survives a genuine self-decoding container. No AI. Draft/do not merge.'}
 json.dump(out,open('imperial_local_hardbox_huffman.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
