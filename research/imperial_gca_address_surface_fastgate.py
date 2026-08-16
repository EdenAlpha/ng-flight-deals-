import json,math,sys
import h5py,numpy as np
sys.path.insert(0,__file__.rsplit('/',1)[0])
import imperial_huber_ar32_coldstart_arithmetic_regions as base

C=8;NT=4096;TRAIN=1024;P=32;TB=1024
REGIONS=(('hard',512),('easy',2304))
STEPS=(160,192,224,240,256,267)
LENS=(2,4,8)
NB=8;NCTX=9*9*NB*4

def clip4(x):return int(max(-4,min(4,int(x))))+4
def zig(k):return (int(k)<<1)^(int(k)>>63)
def ctx(prev,left,pos,pref):return (((clip4(prev)*9+clip4(left))*NB+pos)*4+pref)
def update(counts,k,prev,left):
 u=zig(k)
 if not 0<=u<(1<<NB):return False
 pref=0
 for bp in range(NB-1,-1,-1):
  bit=(u>>bp)&1;pos=NB-1-bp;cx=ctx(prev,left,pos,pref);counts[cx,bit]+=1
  if int(counts[cx].sum())>16384:counts[cx]=(counts[cx]+1)//2
  pref=((pref<<1)|bit)&3
 return True
def prob(counts,k,prev,left):
 u=zig(k)
 if not 0<=u<(1<<NB):return 0.0
 p=1.;pref=0
 for bp in range(NB-1,-1,-1):
  bit=(u>>bp)&1;pos=NB-1-bp;cx=ctx(prev,left,pos,pref);z=counts[cx];p*=float(z[bit])/float(z.sum());pref=((pref<<1)|bit)&3
 return p
def pred(hist,co):
 if len(hist)<P:return 0
 return int(np.rint(float(co[0])+float(np.dot(np.asarray(co[1:],np.float32),np.asarray(hist[-P:][::-1],np.float32)))))
def prefix(X,co,step):
 R=np.zeros((C,TRAIN),np.int32);K=np.zeros((C,TRAIN),np.int32)
 for c in range(C):
  for t in range(TRAIN):
   p=0 if t<P else pred(R[c,:t],co);k=int(np.rint((float(X[c,t])-p)/step));K[c,t]=k;R[c,t]=p+step*k
 return R,K
def lr(x,p,eps,step):return int(math.ceil((float(x)-eps-p)/step-1e-12)),int(math.floor((float(x)+eps-p)/step+1e-12))

def enumerate_paths(X,R,K,co,counts,c,t0,L,step,eps):
 # Each node=(probability, k_list, r_list, private own-channel histories).
 rh=R[c,:t0].copy();kh=K[c,:t0].copy();nodes=[(1.0,[],[],rh,kh)]
 for j in range(L):
  t=t0+j;left=int(K[c-1,t]) if c else 0;new=[]
  for pp,ks,rs,rhist,khist in nodes:
   p=pred(rhist,co);lo,hi=lr(X[c,t],p,eps,step);prev=int(khist[-1]) if len(khist) else 0
   for k in range(lo,hi+1):
    q=prob(counts,k,prev,left)
    if q<=0:continue
    r=p+step*k
    new.append((pp*q,ks+[k],rs+[r],np.append(rhist,np.int32(r)),np.append(khist,np.int32(k))))
  nodes=new
  if not nodes:break
 return nodes

def run(X,co,eps,step,L):
 Rp,Kp=prefix(X,co,step);pbytes,prep,Kpd=base.m.encode_k(Kp)
 if not np.array_equal(Kpd,Kp):raise RuntimeError('prefix')
 R=np.zeros((C,NT),np.int32);K=np.zeros((C,NT),np.int32);R[:,:TRAIN]=Rp;K[:,:TRAIN]=Kp
 counts=np.ones((NCTX,2),np.int32)
 for t in range(TRAIN):
  for c in range(C):update(counts,int(K[c,t]),int(K[c,t-1]) if t else 0,int(K[c-1,t]) if c else 0)
 massbits=mapbits=0.;empty=multi=0;blocks=0;path_counts=[]
 for t0 in range(TRAIN,NT,L):
  for c in range(C):
   nodes=enumerate_paths(X,R,K,co,counts,c,t0,L,step,eps);blocks+=1
   if not nodes:
    empty+=1
    for j in range(L):
     t=t0+j;p=pred(R[c,:t],co);k=int(np.rint((float(X[c,t])-p)/step));K[c,t]=k;R[c,t]=p+step*k;update(counts,k,int(K[c,t-1]) if t else 0,int(K[c-1,t]) if c else 0)
    continue
   path_counts.append(len(nodes));multi+=int(len(nodes)>1);mass=sum(z[0] for z in nodes);best=max(nodes,key=lambda z:z[0]);massbits+=-math.log2(max(mass,1e-300));mapbits+=-math.log2(max(best[0],1e-300))
   _,ks,rs,_,_=best
   for j,(k,r) in enumerate(zip(ks,rs)):
    t=t0+j;K[c,t]=k;R[c,t]=r;update(counts,k,int(K[c,t-1]) if t else 0,int(K[c-1,t]) if c else 0)
 me=float(np.max(np.abs(X-R.astype(np.float64))))
 if me>eps*(1+1e-12):raise RuntimeError(('hard',step,L,me))
 oldc,oldn=base.C,base.NT;base.C,base.NT=C,NT
 try:ab,abit,anb,Kd=base.arithmetic(K)
 finally:base.C,base.NT=oldc,oldn
 if not np.array_equal(Kd,K):raise RuntimeError('K')
 # Independent Huber replay of the chosen exact K path.
 Rd=np.zeros_like(R);Rd[:,:TRAIN]=Rp
 for t0 in range(TRAIN,NT,L):
  for c in range(C):
   for j in range(L):
    t=t0+j;p=pred(Rd[c,:t],co);Rd[c,t]=p+step*int(K[c,t])
 if not np.array_equal(Rd,R):raise RuntimeError(('replay',step,L))
 held=C*(NT-TRAIN);idealbits=massbits+empty*L*NB;idealbytes=base.MODEL_BYTES+int(pbytes)+math.ceil(idealbits/8)+64
 return {'step':step,'L':L,'prefix_bytes':int(pbytes),'actual_map_bytes':int(ab),'actual_map_bps':8*ab/X.size,'ideal_set_bytes':int(idealbytes),'ideal_set_bps':8*idealbytes/X.size,'heldout_set_mass_bps':massbits/held,'heldout_map_nll_bps':mapbits/held,'set_gain_vs_map_nll':mapbits/massbits if massbits else None,'coverage':1-empty/blocks,'multi_path_fraction':multi/blocks,'mean_legal_paths':float(np.mean(path_counts)) if path_counts else 0.,'max_legal_paths':int(max(path_counts)) if path_counts else 0,'zero_fraction':float(np.mean(K[:,TRAIN:]==0)),'k_std':float(np.std(K[:,TRAIN:].astype(np.float64))),'maxerr':me}

def main(path):
 base.C=C;base.NT=NT;base.TRAIN=TRAIN
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,std=base.m.stats(d);eps=.1*std;rows=[];print(json.dumps({'std':std,'eps':eps}),flush=True)
  for region,c0 in REGIONS:
   X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,co=base.fits(X);sz=0
   for t0 in range(0,NT,TB):n,_=base.m.szrun(X[:,t0:t0+TB],eps);sz+=int(n)
   for L in LENS:
    for step in STEPS:
     r=run(X,co,eps,step,L);r.update({'region':region,'c0':c0,'sz3_bytes':sz,'sz3_bps':8*sz/X.size,'gain_actual_vs_sz3':sz/r['actual_map_bytes'],'gain_ideal_set_vs_sz3':sz/r['ideal_set_bytes']});rows.append(r);print(json.dumps(r),flush=True)
   rr=[q for q in rows if q['region']==region];print(json.dumps({'region_summary':region,'best_actual':min(rr,key=lambda q:q['actual_map_bytes']),'best_ideal_set':min(rr,key=lambda q:q['ideal_set_bytes'])},indent=2),flush=True)
 json.dump({'std':std,'eps':eps,'rows':rows,'scope':'Exact corrected GCA address-surface diagnostic. Static Huber decoder state, dense legal lattices, complete enumeration of every legal 2/4/8-sample path, decoder-known adaptive K probabilities, bit-length objective, actual exact MAP K stream, and ideal -log2(total legal probability mass) constrained address. Independent K and source replay. Ideal-set column is diagnostic, not yet a byte container.'},open('imperial_gca_address_surface_fastgate.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
