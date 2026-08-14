import json,sys
import h5py,numpy as np
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as h

C=128;NT=4096;TRAIN=1024;P=32;TB=1024;REGIONS=(('hard',512),('easy',2304));COARSE=(384,512,534,768,1024);REPAIR=267

def h0(a):
 _,n=np.unique(np.asarray(a).ravel(),return_counts=True);p=n/n.sum();return float(-(p*np.log2(p)).sum())

def run(X,co,S):
 R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);Q=np.zeros(X.shape,np.int32);a=float(co[0]);b=np.asarray(co[1:],np.float32)
 for t in range(NT):
  if t<P:pred=np.zeros(C,np.int32)
  else:pred=np.rint(a+R[:,t-P:t][:,::-1].astype(np.float32)@b).astype(np.int32)
  e=X[:,t].astype(np.int64)-pred.astype(np.int64);k=np.rint(e.astype(np.float64)/S).astype(np.int32);base=pred.astype(np.int64)+S*k.astype(np.int64);q=np.rint((X[:,t].astype(np.int64)-base).astype(np.float64)/REPAIR).astype(np.int32);r=base+REPAIR*q.astype(np.int64)
  K[:,t]=k;Q[:,t]=q;R[:,t]=r.astype(np.int32)
 return R,K,Q

def decode(K,Q,co,S):
 R=np.zeros(K.shape,np.int32);a=float(co[0]);b=np.asarray(co[1:],np.float32)
 for t in range(NT):
  if t<P:pred=np.zeros(C,np.int32)
  else:pred=np.rint(a+R[:,t-P:t][:,::-1].astype(np.float32)@b).astype(np.int32)
  R[:,t]=(pred.astype(np.int64)+S*K[:,t].astype(np.int64)+REPAIR*Q[:,t].astype(np.int64)).astype(np.int32)
 return R

def main(path):
 h.C=C;h.NT=NT;h.TRAIN=TRAIN
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
  for region,c0 in REGIONS:
   X=np.asarray(d[:NT,c0:c0+C],np.int16).T.astype(np.int32);XF=X.astype(np.float64);_,co=h.fits(XF);R0,K0=h.run_ar(XF,co);base,n0,nb0,D0=h.arithmetic(K0);RR=h.decode_source(D0,co);me0=float(np.max(np.abs(XF-RR.astype(np.float64))))
   if me0>eps*(1+1e-12):raise RuntimeError((region,'base hard'))
   sz=0
   for t0 in range(0,NT,TB):q,_=m.szrun(XF[:,t0:t0+TB],eps);sz+=int(q)
   variants=[]
   for S in COARSE:
    R,K,Q=run(X,co,S);me=float(np.max(np.abs(XF-R.astype(np.float64))))
    if me>eps*(1+1e-12):raise RuntimeError((region,S,'encoder hard',me,eps))
    kb,kbits,knb,Kd=h.arithmetic(K);qb,qbits,qnb,Qd=h.arithmetic(Q);Rd=decode(Kd,Qd,co,S);dme=float(np.max(np.abs(XF-Rd.astype(np.float64))))
    if not np.array_equal(Kd,K) or not np.array_equal(Qd,Q) or not np.array_equal(Rd,R) or dme>eps*(1+1e-12):raise RuntimeError((region,S,'decode',dme,eps))
    # h.arithmetic charges the shared 177-byte AR model in each stream; retain it only once. Add mode/framing directory.
    total=int(kb)+int(qb)-h.MODEL_BYTES+16
    row={'coarse_step':S,'repair_step':REPAIR,'bytes':total,'bps':8*total/X.size,'coarse_stream_bytes':int(kb),'repair_stream_bytes':int(qb),'coarse_bits':int(kbits),'repair_bits':int(qbits),'coarse_symbol_bits':int(knb),'repair_symbol_bits':int(qnb),'coarse_h0_bps':h0(K),'repair_h0_bps':h0(Q),'repair_zero_fraction':float(np.mean(Q==0)),'repair_abs1_fraction':float(np.mean(np.abs(Q)==1)),'maxerr':dme,'gain_vs_step267':base/total,'gain_vs_sz3':sz/total,'ratio_to_2x_target':total/(sz/2)}
    variants.append(row);print(json.dumps({'region':region,'variant':row},indent=2),flush=True)
   best=min(variants,key=lambda z:z['bytes']);outrow={'region':region,'c0':c0,'samples':int(X.size),'eps':eps,'step267_bytes':int(base),'step267_bps':8*base/X.size,'sz3_bytes':sz,'sz3_bps':8*sz/X.size,'best':best,'variants':variants};rows.append(outrow);print(json.dumps({'summary':outrow},indent=2),flush=True)
  out={'global_std':gstd,'eps':eps,'shape':[C,NT],'coarse_steps':list(COARSE),'repair_step':REPAIR,'rows':rows,'scope':'Constructive two-layer decoder-real Huber AR32 pilot. For each sample, the predictor is computed from the final already-repaired reconstruction. The current innovation first selects a coarse symbol k=round((X-P)/S), S in {384,512,534,768,1024}; provisional base B=P+S*k is then certified with q=round((X-B)/267), yielding final R=B+267q and deterministic <=133.5 hard error below epsilon. The final repaired R becomes future predictor state. Coarse and repair symbol fields are independently encoded/decoded with the incumbent cold-start contextual arithmetic backend; the shared AR model is charged once, both arithmetic framings and an explicit layer directory are charged, and the complete recursive source is regenerated. Exact step267 Huber AR32 and matched SZ3 controls are rerun on hard/easy 128x4096 regions. This tests whether a low-entropy coarse trajectory plus sparse hard-error certificate beats direct one-layer symbols. No AI. Draft/do not merge.'};json.dump(out,open('imperial_ar32_coarse_layer_hard_repair.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
