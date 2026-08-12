import json,sys,math
import h5py,numpy as np

NS=(2,4,8,16,32);NCH=32;PHASES=64

def stats(d):
 s=ss=0.;n=0
 for t0 in range(0,d.shape[0],2048):
  x=np.asarray(d[t0:min(d.shape[0],t0+2048)],np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
 m=s/n;return m,math.sqrt(max(0.,ss/n-m*m))
def H(a):
 _,c=np.unique(np.asarray(a).ravel(),return_counts=True);p=c/c.sum();return float(-(p*np.log2(p)).sum())
def choose_phase(d,eps):
 step=2*eps;tt=np.linspace(0,d.shape[0]-1,1024,dtype=np.int32);cc=np.linspace(0,d.shape[1]-1,256,dtype=np.int32);x=np.asarray(d[tt,:],np.float64)[:,cc].ravel();best=None
 for k in range(PHASES):
  ph=step*k/PHASES;q=np.floor((x+ph)/step).astype(np.int32);h=H(q)
  if best is None or h<best[0]:best=(h,ph,k)
 return best
def qcol(d,c,step,ph):return np.floor((np.asarray(d[:,c],np.float64)+ph)/step).astype(np.int32)
def blocks(q,n):
 m=len(q)//n*n;return np.ascontiguousarray(q[:m].reshape(-1,n),np.int32)
def shape(A,pol=False):
 D=A-A[:,0:1]
 if not pol:return D,np.zeros(len(D),np.uint8)
 # canonicalize sign using first nonzero component
 S=np.ones(len(D),np.int8)
 for j in range(1,D.shape[1]):
  z=(S==1)&(D[:,j]!=0);S[z]=np.where(D[z,j]<0,-1,2);S[S==2]=1
 # redo cleanly: sign=-1 iff first nonzero is negative
 sg=np.ones(len(D),np.int8);und=np.ones(len(D),bool)
 for j in range(1,D.shape[1]):
  take=und&(D[:,j]!=0);sg[take]=np.where(D[take,j]<0,-1,1);und[take]=False
 return D*sg[:,None],(sg<0).astype(np.uint8)
def rowkeys(A):
 B=np.ascontiguousarray(A,dtype='<i4');return B.view(np.dtype((np.void,B.dtype.itemsize*B.shape[1]))).ravel()
def model_bits_rows(P,T):
 pk=rowkeys(P);tk=rowkeys(T);u,c=np.unique(pk,return_counts=True);pos=np.searchsorted(u,tk);seen=pos<len(u);seen&=np.where(seen,u[np.minimum(pos,len(u)-1)]==tk,False)
 bits=np.zeros(len(T),np.float64);bits[seen]=-np.log2(c[pos[seen]].astype(np.float64)/len(P));return bits,seen,int(len(u))
def model_bits_scalar(P,T):
 vals,c=np.unique(P,return_counts=True);lo=int(min(vals.min(),T.min()));hi=int(max(vals.max(),T.max()));K=hi-lo+1;cnt=np.zeros(K,np.float64)+0.25;cnt[vals-lo]+=c;prob=cnt/cnt.sum();return -np.log2(prob[T-lo])
def eval_model(P,T,n,literal_bps,pol):
 Ps,ps=shape(P,pol);Ts,ts=shape(T,pol);sbits,seen,vocab=model_bits_rows(Ps,Ts);abits=model_bits_scalar(P[:,0],T[:,0]);bits=np.empty(len(T),np.float64)
 # one raw mode bit: 0=known shape, 1=escape. Known pays model shape + anchor + polarity flag if used.
 bits[seen]=1+sbits[seen]+abits[seen]+(1 if pol else 0);bits[~seen]=1+n*literal_bps
 return {'bps':float(bits.sum()/(len(T)*n)),'seen_fraction':float(seen.mean()),'shape_vocab':vocab,'known_shape_bps':float(np.mean((sbits[seen]+abits[seen]+(1 if pol else 0))/n)) if np.any(seen) else None}
def main(paths):
 fs=[h5py.File(p,'r') for p in paths]
 try:
  ds=[f['Acoustic'] for f in fs];_,std=stats(ds[-1]);eps=.1*std;step=2*eps;_,ph,pidx=choose_phase(ds[-1],eps);chs=np.linspace(0,6911,NCH,dtype=np.int32);Q=[[qcol(d,int(c),step,ph) for c in chs] for d in ds];literal=float(np.mean([H(q) for q in Q[-1]]));rows=[]
  for n in NS:
   tar=[blocks(q,n) for q in Q[-1]];prev=[[blocks(q,n) for q in QQ] for QQ in Q[:-1]]
   for pol in (False,True):
    same=[]
    for ci,T in enumerate(tar):same.append((len(T),eval_model(np.concatenate([prev[0][ci],prev[1][ci]]),T,n,literal,pol)))
    pooled=eval_model(np.concatenate([a for pp in prev for a in pp]),np.concatenate(tar),n,literal,pol)
    rows.append({'phrase_length':n,'polarity_canonical':pol,'same_channel_bps':sum(nn*r['bps'] for nn,r in same)/sum(nn for nn,_ in same),'same_channel_seen_fraction':sum(nn*r['seen_fraction'] for nn,r in same)/sum(nn for nn,_ in same),'pooled_corpus_bps':pooled['bps'],'pooled_seen_fraction':pooled['seen_fraction'],'pooled_shape_vocab':pooled['shape_vocab'],'pooled_known_shape_bps':pooled['known_shape_bps']})
  rows.sort(key=lambda r:r['same_channel_bps']);out={'files':3,'channels':chs.tolist(),'std':std,'eps':eps,'step':step,'phase':ph,'phase_index':pidx,'literal_scalar_bps':literal,'fullfile_sz3_bps':8*86361271/(30000*6912),'strict_2x_target_bps':(8*86361271/(30000*6912))/2,'rows':rows,'scope':'Sequential-corpus quotient-language diagnostic. Each hard-error lattice phrase is represented as a translation-invariant shape q-q0 plus one scalar anchor; optional polarity canonicalization. Previous two decoded-lattice minutes deterministically define shape dictionaries/probabilities. One raw escape flag is charged per phrase; unseen shapes fall back to full scalar literal cost. No absolute-location pointers and no target-trained phrase probabilities.'}
  print(json.dumps(out,indent=2),flush=True);json.dump(out,open('imperial_quotient_shape_language.json','w'),indent=2)
 finally:
  for f in fs:f.close()
if __name__=='__main__':main(sys.argv[1:])
