import json,sys,importlib.util
import h5py,numpy as np
spec=importlib.util.spec_from_file_location('g','research/imperial_physical_gauge_operator.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
SPECS=(('hard',14488,0),('easy',14488,2304))
def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,std=g.stats(d);eps=.1*std;b=eps*g.SAFETY;step=2*b;rows=[]
  for name,t0,c0 in SPECS:
   X=np.asarray(d[t0:t0+g.T,c0:c0+g.C],np.float64).T;sb=g.szrun(X,eps);mb,M=g.encode_mean(X.mean(axis=0));X0=X-M[None,:]
   for ap in (1.0,2.5):
    H=g.gauge_H(ap);U0=g.inverse(X0,H)
    for k in (4,8):
     for rounds in (0,2):
      U=U0.copy()
      for _ in range(rounds):
       _,_,L=g.rankproj(U,k);P=M[None,:]+g.forward(L,H);Y=np.clip(P,X-b,X+b);U=g.inverse(Y-M[None,:],H)
      Q,W,L=g.rankproj(U,k);fb,Ld=g.encode_factors(Q,W,'q16');P=M[None,:]+g.forward(Ld,H);K=np.rint((X-P)/step).astype(np.int32);kb,krep,Kd=g.encode_K(K);R=P+step*Kd;me=float(np.max(np.abs(X-R)))
      if me>eps*(1+5e-6):raise RuntimeError(('hard',name,ap,k,rounds,me))
      total=mb+fb+kb+64;rows.append({'tile':name,'aperture_channels':ap,'rank':k,'rounds':rounds,'bytes':total,'bps':8*total/X.size,'sz3_bytes':sb[0],'gain_vs_sz3':sb[0]/total,'correction_nonzero_fraction':float(np.mean(K!=0)),'model_rmse_over_eps':float(np.sqrt(np.mean((X-P)**2))/eps),'correction_bytes':kb,'factor_bytes':fb,'mean_bytes':mb,'correction_rep':krep,'maxerr':me})
  best={}
  for tile in ('hard','easy'):
   rr=[r for r in rows if r['tile']==tile];best[tile]=sorted(rr,key=lambda r:r['bytes'])[:6]
  out={'std':std,'eps':eps,'best':best,'rows':rows,'scope':'Two-tile fast gate of PR273. Directly compares aperture-1 adjacent finite difference with physical 10m/4m=2.5-channel gauge operator at ranks 4/8 and 0/2 measurement-box projection rounds, q16 latent factors, fully decoded correction bytes, unchanged hard error.'}
  print(json.dumps(out,indent=2),flush=True);json.dump(out,open('imperial_physical_gauge_fastgate.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
