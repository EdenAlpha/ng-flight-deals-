import json,sys,math
import h5py,numpy as np

NCH=32;NS=(4,8,16);SF=(0.5,0.75,1.0,1.25,1.5);SAFETY=1-1e-6

def stats(d):
 s=ss=0.;n=0
 for i in range(0,d.shape[0],2048):
  x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
 m=s/n;return m,math.sqrt(max(0.,ss/n-m*m))
def blocks(x,n):
 m=len(x)//n*n;return np.asarray(x[:m],np.float64).reshape(-1,n)
def fit_block(A,eps,hs,ha,model=None):
 D=A-A[:,0:1];Q=np.rint(D[:,1:]/hs).astype(np.int32);S=np.zeros_like(A);S[:,1:]=hs*Q;R=A-S;L=np.max(R-eps,axis=1);H=np.min(R+eps,axis=1);lo=np.ceil(L/ha-1e-12).astype(np.int32);hi=np.floor(H/ha+1e-12).astype(np.int32)
 if np.any(lo>hi):raise RuntimeError(('empty offset interval',float(np.min(H-L)),ha,hs))
 mid=np.rint(0.5*(L+H)/ha).astype(np.int32);K=np.minimum(np.maximum(mid,lo),hi)
 if model is not None:
  for j in range(len(K)):
   best=K[j];bb=model_bits(np.asarray([best],np.int32),model)[0]
   for k in range(int(lo[j]),int(hi[j])+1):
    b=model_bits(np.asarray([k],np.int32),model)[0]
    if b<bb:bb=b;best=k
   K[j]=best
 Rec=S+ha*K[:,None];me=float(np.max(np.abs(A-Rec)))
 if me>eps*(1+3e-6):raise RuntimeError(('hard error',me,eps,hs,ha))
 return Q,K,me,float(np.mean(hi-lo+1))
def make_model(a):
 a=np.asarray(a,np.int32).ravel();u,c=np.unique(a,return_counts=True);lo=int(u.min());hi=int(u.max());cnt=np.zeros(hi-lo+1,np.float64)+0.25;cnt[u-lo]+=c;return lo,cnt/cnt.sum()
def model_bits(a,m):
 lo,p=m;a=np.asarray(a,np.int32);ix=a-lo;out=np.full(a.shape,16.0,np.float64);ok=(ix>=0)&(ix<len(p));out[ok]=-np.log2(np.maximum(p[ix[ok]],1e-300));return out
def channel_rate(prev,target,n,eps,hs,ha):
 PB=[blocks(p,n) for p in prev];P=np.concatenate(PB,axis=0);PQ,PK,_,_=fit_block(P,eps,hs,ha);am=make_model(PK);sm=[make_model(PQ[:,j]) for j in range(PQ.shape[1])];T=blocks(target,n);TQ,TK,me,freedom=fit_block(T,eps,hs,ha,am);bits=model_bits(TK,am)
 for j,m in enumerate(sm):bits+=model_bits(TQ[:,j],m)
 return {'bps':float(bits.sum()/(len(T)*n)),'offset_bps_per_block':float(model_bits(TK,am).mean()),'shape_bps_per_block':float(sum(model_bits(TQ[:,j],sm[j]).mean() for j in range(TQ.shape[1]))),'mean_legal_offset_states':freedom,'maxerr':me}
def main(paths):
 fs=[h5py.File(p,'r') for p in paths]
 try:
  ds=[f['Acoustic'] for f in fs];_,std=stats(ds[-1]);eps=.1*std;chs=np.linspace(0,6911,NCH,dtype=np.int32);rows=[]
  for sf in SF:
   hs=sf*eps;ha=(2*eps-hs)*SAFETY
   for n in NS:
    rr=[]
    for c in chs:
     prev=[np.asarray(ds[k][:,int(c)],np.float64) for k in (0,1)];tar=np.asarray(ds[2][:,int(c)],np.float64);rr.append(channel_rate(prev,tar,n,eps,hs,ha))
    rows.append({'shape_step_over_eps':sf,'offset_step_over_eps':ha/eps,'phrase_length':n,'same_channel_bps':float(np.mean([r['bps'] for r in rr])),'offset_bits_per_phrase':float(np.mean([r['offset_bps_per_block'] for r in rr])),'shape_bits_per_phrase':float(np.mean([r['shape_bps_per_block'] for r in rr])),'mean_legal_offset_states':float(np.mean([r['mean_legal_offset_states'] for r in rr])),'maxerr':max(r['maxerr'] for r in rr)})
  rows.sort(key=lambda r:r['same_channel_bps']);out={'files':3,'channels':chs.tolist(),'std':std,'eps':eps,'fullfile_sz3_bps':8*86361271/(30000*6912),'strict_2x_target_bps':(8*86361271/(30000*6912))/2,'rows':rows,'scope':'Distortion-quotient coordinate audit. Each n-sample block is encoded as n-1 relative-shape lattice coordinates plus one common offset. Shape step hs and offset step ha obey ha < 2eps-hs, so nearest relative-shape errors guarantee a nonempty legal offset-grid interval and therefore the original max-error contract. Previous two minutes define per-channel static models; target offset is chosen from its legal interval to minimize previous-model codelength. No target-trained probabilities. Ideal arithmetic component rate only.'}
  print(json.dumps(out,indent=2),flush=True);json.dump(out,open('imperial_distortion_quotient_coordinates.json','w'),indent=2)
 finally:
  for f in fs:f.close()
if __name__=='__main__':main(sys.argv[1:])
