import json,sys
import h5py,numpy as np,zstandard as zstd
import imperial_dyadic_legal_grid_full_array as m

MODS=(4,16,256);OBJECTIVES=('l1','bitflip')
SPECS=(('hard',14488,512),('easy',14488,2304),('medium',14488,4608),('far',14488,6784))
Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor()
POPC=np.array([int(i).bit_count() for i in range(65536)],dtype=np.uint8)

def zz(a):
 a=np.asarray(a,np.int64);return ((a<<1)^(a>>63)).astype(np.uint64)
def ecost_batch(A,B,kind,axis=None):
 # A/B broadcastable with first dimension candidate M.
 if kind=='l1':return np.abs(A.astype(np.int64)-B.astype(np.int64)).sum(axis=axis)
 x=np.bitwise_xor(zz(A),zz(B))
 if int(x.max(initial=0))>=POPC.size:
  # not expected for coarse int16 high-byte symbols
  v=np.vectorize(lambda q:int(q).bit_count(),otypes=[np.int16])(x)
 else:v=POPC[x.astype(np.int64)]
 return v.sum(axis=axis)
def B_from_index(X,idx,M):
 H=256.0/M;ph=H*np.asarray(idx,np.float64)
 return np.rint((X-ph)/256.0).astype(np.int32)
def full_proxy(B,kind):
 return int(ecost_batch(B[:,:-1],B[:,1:],kind,None)+ecost_batch(B[:-1,:],B[1:,:],kind,None))

def initial(nc,nt,M,k,X):
 if k==0:return np.zeros(nc,np.int32),np.zeros(nt,np.int32)
 # Decoder ultimately receives these factors, so data-dependent initialization is fully charged.
 low=np.mod(np.rint(X).astype(np.int64),256).astype(np.float64)
 H=256.0/M
 if k==1:
  r=np.mod(np.rint(np.median(low,axis=1)/H),M).astype(np.int32);s=np.zeros(nt,np.int32);return r,s
 if k==2:
  r=np.zeros(nc,np.int32);s=np.mod(np.rint(np.median(low,axis=0)/H),M).astype(np.int32);return r,s
 rng=np.random.default_rng(20260812+M+k);return rng.integers(0,M,nc,dtype=np.int32),rng.integers(0,M,nt,dtype=np.int32)

def optimize(X,M,kind,init_id,maxpass):
 nc,nt=X.shape;r,s=initial(nc,nt,M,init_id,X);H=256.0/M
 idx=(r[:,None]+s[None,:])%M;B=B_from_index(X,idx,M);vals=np.arange(M,dtype=np.int32)
 flips=0
 for _ in range(maxpass):
  changed=0
  for c in range(nc):
   ids=(vals[:,None]+s[None,:])%M;ph=H*ids.astype(np.float64)
   cand=np.rint((X[c][None,:]-ph)/256.0).astype(np.int32)
   cost=ecost_batch(cand[:,:-1],cand[:,1:],kind,1)
   if c:cost=cost+ecost_batch(cand,B[c-1][None,:],kind,1)
   if c+1<nc:cost=cost+ecost_batch(cand,B[c+1][None,:],kind,1)
   j=int(np.argmin(cost))
   if j!=int(r[c]):r[c]=j;B[c]=cand[j];changed+=1;flips+=1
  for t in range(nt):
   ids=(r[None,:]+vals[:,None])%M;ph=H*ids.astype(np.float64)
   cand=np.rint((X[:,t][None,:]-ph)/256.0).astype(np.int32)
   cost=ecost_batch(cand[:,:-1],cand[:,1:],kind,1)
   if t:cost=cost+ecost_batch(cand,B[:,t-1][None,:],kind,1)
   if t+1<nt:cost=cost+ecost_batch(cand,B[:,t+1][None,:],kind,1)
   j=int(np.argmin(cost))
   if j!=int(s[t]):s[t]=j;B[:,t]=cand[j];changed+=1;flips+=1
  if not changed:break
 return r,s,B,full_proxy(B,kind),flips

def encode_B(B):
 c=m.signed_reps(B)+m.xor_reps(B)+[m.bitplane_rep(B,False),m.bitplane_rep(B,True),m.byteshuffle_rep(B)]
 return min(c,key=lambda x:x[0])
def factor_blob(a,M):
 dt=np.uint8 if M<=256 else np.uint16;raw=np.asarray(a,dtype=dt).tobytes();bb=Z.compress(raw);rr=np.frombuffer(D.decompress(bb),dtype=dt,count=len(a)).astype(np.int32)
 if not np.array_equal(rr,a):raise RuntimeError('factor roundtrip')
 return bb,rr

def materialize(X,eps,M,r,s,B):
 rb,rd=factor_blob(r,M);sb,sd=factor_blob(s,M);best=encode_B(B);Bd=best[2].astype(np.int32)
 idx=(rd[:,None]+sd[None,:])%M;R=(256.0/M)*idx.astype(np.float64)+256.0*Bd.astype(np.float64);me=float(np.max(np.abs(X-R)))
 if me>eps*(1+5e-6):raise RuntimeError(('hard',M,me,eps))
 total=int(best[0])+len(rb)+len(sb)+80
 return {'bytes':total,'bps':8*total/X.size,'B_bytes':int(best[0]),'B_rep':best[1],'factor_bytes':len(rb)+len(sb),'factor_bps':8*(len(rb)+len(sb))/X.size,'maxerr':me,'B_edge_fraction':float((np.count_nonzero(B[:,:-1]!=B[:,1:])+np.count_nonzero(B[:-1,:]!=B[1:,:]))/(B[:,:-1].size+B[:-1,:].size)),'phase_unique':int(np.unique(idx).size)}

def evaluate(X,eps,M):
 rows=[];r0=np.zeros(X.shape[0],np.int32);s0=np.zeros(X.shape[1],np.int32);B0=np.rint(X/256.0).astype(np.int32)
 z=materialize(X,eps,M,r0,s0,B0);z.update({'kind':'phase0','objective':'none','init':0,'proxy':None,'flips':0});rows.append(z)
 passes=3 if M<256 else 2
 ninits=4 if M<256 else 3
 for obj in OBJECTIVES:
  cand=[]
  for k in range(ninits):
   r,s,B,p,fl=optimize(X,M,obj,k,passes);q=materialize(X,eps,M,r,s,B);q.update({'kind':'zm_gauge','objective':obj,'init':k,'proxy':p,'flips':fl});cand.append(q)
  rows.append(min(cand,key=lambda x:x['bytes']))
 return rows

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;rows=[];tiles=[]
  for name,t0,c0 in SPECS:
   X=np.asarray(d[t0:t0+m.TB,c0:c0+m.CB],np.float64).T;sb,ori=m.szrun(X,eps);tiles.append({'tile':name,'sz3_bytes':sb,'sz3_bps':8*sb/X.size,'orientation':ori})
   for M in MODS:
    for r in evaluate(X,eps,M):
     r.update({'tile':name,'modulus':M,'phase_step':256.0/M,'sz3_bytes':sb,'gain_vs_sz3':sb/r['bytes']});rows.append(r);print(json.dumps(r),flush=True)
  combos=[]
  for M in MODS:
   for kind,obj in [('phase0','none')]+[('zm_gauge',o) for o in OBJECTIVES]:
    rr=[r for r in rows if r['modulus']==M and r['kind']==kind and r['objective']==obj];b=sum(r['bytes'] for r in rr);s=sum(t['sz3_bytes'] for t in tiles);n=m.CB*m.TB*len(rr)
    combos.append({'modulus':M,'phase_step':256.0/M,'kind':kind,'objective':obj,'bytes':b,'sz3_bytes':s,'bps':8*b/n,'gain_vs_sz3':s/b,'mean_factor_bps':float(np.mean([r['factor_bps'] for r in rr])),'median_B_edge_fraction':float(np.median([r['B_edge_fraction'] for r in rr])),'median_phase_unique':float(np.median([r['phase_unique'] for r in rr])),'min_tile_gain':min(r['gain_vs_sz3'] for r in rr)})
  combos.sort(key=lambda x:x['bytes'])
  out={'global_std':std,'eps':eps,'moduli':list(MODS),'patch_shape':[m.CB,m.TB],'objectives':list(OBJECTIVES),'specs':[list(x) for x in SPECS],'combos':combos,'rows':rows,'scope':'Modular low-description phase-gauge synthesis. Since public epsilon exceeds 128, for any phase phi in [0,255] the nearest point on phi+256Z is hard-error legal. A phase field is therefore a distortion control variable. This branch constrains phase index to (r(channel)+s(time)) mod M for M=4,16,256, giving M^(C+T-1) legal phase fields while transmitting only C+T small factors. Coordinate descent optimizes those factors against coarse-byte L1 or zigzag bit-transition cost. Factors and the exact coarse B field are Zstd serialized/byte-decoded, the phase field regenerated, and final samples hard-error verified. B uses exact PR287/288 decoder-real representations; matched SZ3 is rerun on identical 128x1024 hard/easy/medium/far tiles. No AI, patch screen only.'}
  print(json.dumps({'combos':combos},indent=2),flush=True);json.dump(out,open('imperial_zm_phase_gauge_control.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
