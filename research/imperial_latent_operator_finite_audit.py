import json,sys,os
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np,h5py,zstandard as zstd
from research.imperial_latent_mixed_operator_codeword import stats,project_candidate,szrun,diff2,encode_corr

C=128;T=1024;SAFETY=1-1e-5;RANKS=(2,4,8);ROUNDS=(0,2,8);SPECS=(('easy',14488,1696),('medium',14488,3392),('hard',14488,6784));Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor()

def blob(a):return Z.compress(np.ascontiguousarray(a).tobytes())
def unblob(b,dt,shape):return np.frombuffer(D.decompress(b),dtype=dt,count=int(np.prod(shape))).reshape(shape)
def finite(a,name):
 if not np.all(np.isfinite(a)):raise RuntimeError(('nonfinite',name,int(np.size(a)-np.count_nonzero(np.isfinite(a)))))

def factor_safe(Q,H,mode):
 finite(Q,'Q');finite(H,'H');k=Q.shape[1]
 if mode.startswith('sf16'):
  sdt=np.float32 if mode=='sf16_f32scale' else np.float64
  hs=np.maximum(np.max(np.abs(H),axis=1),1e-300).astype(sdt);hn=H/hs.astype(np.float64)[:,None]
  qb=blob(Q.astype(np.float16));hb=blob(hn.astype(np.float16));sb=blob(hs)
  qd=unblob(qb,np.float16,Q.shape).astype(np.float64);hnd=unblob(hb,np.float16,H.shape).astype(np.float64);hsd=unblob(sb,sdt,(k,)).astype(np.float64);R=qd@(hnd*hsd[:,None]);finite(R,'scaled-f16-R')
  return R,len(qb)+len(hb)+len(sb)+56
 qmax=127.;qs=np.maximum(np.max(np.abs(Q),axis=0)/qmax,1e-300).astype(np.float32);qq=np.rint(Q/qs.astype(np.float64)).clip(-127,127).astype(np.int8)
 hbits=8 if mode=='q8q8_safe' else 16;hmax=127. if hbits==8 else 32767.;hdt=np.int8 if hbits==8 else np.dtype('<i2');hs=np.maximum(np.max(np.abs(H),axis=1)/hmax,1e-300).astype(np.float32);hq=np.rint(H/hs.astype(np.float64)[:,None]).clip(-hmax,hmax).astype(hdt)
 qb=blob(qq);hb=blob(hq);qsb=blob(qs);hsb=blob(hs);qqd=unblob(qb,np.int8,Q.shape).astype(np.float64);hqd=unblob(hb,hdt,H.shape).astype(np.float64);qsd=unblob(qsb,np.float32,(k,)).astype(np.float64);hsd=unblob(hsb,np.float32,(k,)).astype(np.float64);R=(qqd*qsd[None,:])@(hqd*hsd[:,None]);finite(R,mode+'-R')
 return R,len(qb)+len(hb)+len(qsb)+len(hsb)+72

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,std=stats(d);eps=.1*std;b=eps*SAFETY;step=2*b;rows=[];tiles=[]
  for name,t0,c0 in SPECS:
   X=np.asarray(d[t0:t0+T,c0:c0+C],np.float64).T;finite(X,'X');sb=szrun(X,eps);tiles.append({'tile':name,'sz3':sb})
   for k in RANKS:
    for method in ('ap','dr'):
     for rounds in ROUNDS:
      v,frac,rm,it,Q,H,R=project_candidate(X,b,k,rounds,method)
      for mode in ('sf16_f32scale','sf16_f64scale','q8q8_safe','q8q16_safe'):
       P,fb=factor_safe(Q,H,mode);P=diff2(P);finite(P,'prediction');res=X-P;finite(res,'residual');kr=np.rint(res/step);finite(kr,'rounded-correction')
       if np.max(np.abs(kr))>2147483000:raise RuntimeError('correction overflow')
       K=kr.astype(np.int32);cb,nzf=encode_corr(K);Xh=P+step*K;finite(Xh,'reconstruction');me=float(np.max(np.abs(X-Xh)))
       if not np.isfinite(me) or me>eps*(1+5e-6):raise RuntimeError(('hard-error',name,k,method,rounds,mode,me,eps))
       total=fb+cb[0]+80;rows.append({'tile':name,'rank':k,'method':method,'rounds':rounds,'factor_mode':mode,'factor_bytes':fb,'correction_bytes':cb[0],'correction_rep':cb[1],'correction_nonzero_fraction':nzf,'total_bytes':total,'sz3_bytes':sb,'gain_vs_sz3':sb/total,'bps':8*total/X.size,'maxerr':me,'prequant_violation_fraction':frac,'prequant_rmse_over_eps':rm/eps})
  combos=[]
  for k in RANKS:
   for method in ('ap','dr'):
    for rounds in ROUNDS:
     for mode in ('sf16_f32scale','sf16_f64scale','q8q8_safe','q8q16_safe'):
      rr=[r for r in rows if r['rank']==k and r['method']==method and r['rounds']==rounds and r['factor_mode']==mode];bs=sum(r['total_bytes'] for r in rr);ss=sum(r['sz3_bytes'] for r in rr);combos.append({'rank':k,'method':method,'rounds':rounds,'factor_mode':mode,'bytes':bs,'sz3_bytes':ss,'gain_vs_sz3':ss/bs,'bps':8*bs/(C*T*len(rr)),'min_tile_gain':min(r['gain_vs_sz3'] for r in rr),'factor_bytes':sum(r['factor_bytes'] for r in rr),'correction_bytes':sum(r['correction_bytes'] for r in rr),'median_correction_nonzero':float(np.median([r['correction_nonzero_fraction'] for r in rr]))})
  combos.sort(key=lambda r:r['bytes']);out={'std':std,'eps':eps,'combos':combos,'rows':rows,'invalidated_parent_claim':'PR243 unscaled float16 mode produced nonfinite decoded factors and NaN max-error; those rows are rejected here before correction or byte accounting.','scope':'Finite-safe rerun. Every factor scale is explicitly serialized, byte-decoded, and counted. Nonfinite factor/prediction/residual/correction/reconstruction is a hard failure before acceptance. Three precommitted tiles; one fixed definition in aggregate.'};print(json.dumps({'best':combos[:12]},indent=2),flush=True);json.dump(out,open('imperial_latent_operator_finite_audit.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
