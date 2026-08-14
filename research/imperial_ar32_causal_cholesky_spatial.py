import json,sys
import h5py,numpy as np,zstandard as zstd
import imperial_huber_ar32_coldstart_arithmetic_regions as h
import imperial_decoder_phase_automaton as m

C=128;NT=8192;TRAIN=1024;P=32;STEP=267;TB=1024
REGIONS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
WIDTHS=(4,8,16,32)
Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor()

def fit_matrix(E,L):
 B=np.zeros((C,L),np.float32)
 for c in range(1,C):
  q=min(L,c);A=np.asarray(E[c-q:c,:TRAIN].T,np.float64);y=np.asarray(E[c,:TRAIN],np.float64)
  G=A.T@A;lam=1e-4*float(np.trace(G))/max(1,q);co=np.linalg.solve(G+lam*np.eye(q),A.T@y)
  B[c,L-q:]=co.astype(np.float32)
 raw=np.ascontiguousarray(B).astype('<f4').tobytes();bb=Z.compress(raw);Bd=np.frombuffer(D.decompress(bb),'<f4').reshape(C,L).copy()
 if not np.array_equal(Bd,B):raise RuntimeError('coefficient decode')
 return Bd,len(bb)+32

def run_codec(X,ar,B):
 L=B.shape[1];R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);a=float(ar[0]);b=np.asarray(ar[1:],np.float32)
 for t in range(NT):
  er=np.zeros(C,np.int32)
  for c in range(C):
   tp=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
   q=min(L,c);sc=0.0 if q==0 else float(np.dot(B[c,L-q:].astype(np.float32),er[c-q:c].astype(np.float32)))
   pred=tp+int(np.rint(sc));k=int(np.rint((float(X[c,t])-pred)/STEP));K[c,t]=k;R[c,t]=pred+STEP*k;er[c]=R[c,t]-tp
 return R,K

def decode_codec(K,ar,B):
 L=B.shape[1];R=np.zeros(K.shape,np.int32);a=float(ar[0]);b=np.asarray(ar[1:],np.float32)
 for t in range(K.shape[1]):
  er=np.zeros(C,np.int32)
  for c in range(C):
   tp=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
   q=min(L,c);sc=0.0 if q==0 else float(np.dot(B[c,L-q:].astype(np.float32),er[c-q:c].astype(np.float32)))
   pred=tp+int(np.rint(sc));R[c,t]=pred+STEP*int(K[c,t]);er[c]=R[c,t]-tp
 return R

def main(path):
 h.C=C;h.NT=NT;h.TRAIN=TRAIN
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gs=m.stats(d);eps=.1*gs;rows=[]
  for region,c0 in REGIONS:
   X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,ar=h.fits(X);R0,K0=h.run_ar(X,ar);P0=R0.astype(np.float64)-STEP*K0.astype(np.float64);E=X-P0
   base_backend,_=h.backend_bytes(K0);base_arith,_,_,D0=h.arithmetic(K0);Rd0=h.decode_source(D0,ar)
   if not np.array_equal(Rd0,R0):raise RuntimeError((region,'baseline decode'))
   sz=0
   for t0 in range(0,NT,TB):q,_=m.szrun(X[:,t0:t0+TB],eps);sz+=int(q)
   cand=[];keep={}
   for L in WIDTHS:
    B,model=fit_matrix(E,L);R,K=run_codec(X,ar,B);me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+1e-12):raise RuntimeError((region,L,'hard',me,eps))
    n,reps=h.backend_bytes(K);n+=model;z={'width':L,'backend_bytes':int(n),'backend_bps':8*n/X.size,'model_bytes':model,'gain_backend_vs_baseline':base_backend/n,'gain_backend_vs_sz3':sz/n,'k_std':float(K.std()),'k_zero_fraction':float(np.mean(K==0)),'maxerr':me,'reps':reps};cand.append(z);keep[L]=(B,R,K);print(json.dumps({'region':region,**{k:v for k,v in z.items() if k!='reps'}},indent=2),flush=True)
   best=min(cand,key=lambda z:z['backend_bytes']);B,R,K=keep[best['width']];cab,nbits,sbits,Kd=h.arithmetic(K);cab+=best['model_bytes'];Rd=decode_codec(Kd,ar,B);me=float(np.max(np.abs(X-Rd.astype(np.float64))))
   if not np.array_equal(Kd,K) or not np.array_equal(Rd,R) or me>eps*(1+1e-12):raise RuntimeError((region,'arithmetic decode',me,eps))
   final={'width':best['width'],'bytes':int(cab),'bps':8*cab/X.size,'model_bytes':best['model_bytes'],'gain_vs_step267_arithmetic':base_arith/cab,'gain_vs_sz3':sz/cab,'arithmetic_bits':int(nbits),'symbol_bits':int(sbits),'maxerr':me}
   row={'region':region,'c0':c0,'samples':int(X.size),'step267_arithmetic_bytes':int(base_arith),'step267_arithmetic_bps':8*base_arith/X.size,'sz3_bytes':sz,'sz3_bps':8*sz/X.size,'best':final,'backend_candidates':cand};rows.append(row);print(json.dumps({'summary':row},indent=2),flush=True)
  json.dump({'eps':eps,'widths':list(WIDTHS),'rows':rows,'scope':'Banded causal spatial whitening after decoder-real Huber AR32. A separate prefix-trained lower-triangular regression is learned for every channel from the preceding 4/8/16/32 current-time temporal residuals. During time-major decoding, those previous-channel reconstructed residuals are already known, so no transformed-vector shape penalty is introduced. Float32 coefficient matrices are Zstd-compressed, byte-decoded and charged. Candidate K streams are exactly decoded; the best backend width is rerun through the incumbent cold-start arithmetic coder and the full recursive source is hard-error verified.'},open('imperial_ar32_causal_cholesky_spatial.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
