import json,sys
import h5py,numpy as np
import imperial_near2eps_learned_zsm_fullhard as q
import imperial_near2eps_scale_128x4096 as sc
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m
q.f.q_decode=sc.q_decode
GRAMMARS=('none','slopes9','slopes_prev27','slopes_prev_band4')
BIAS_LIM=32

def s3(x):return np.where(x<0,0,np.where(x>0,2,1)).astype(np.int16)
def contexts(Q,D,grammar):
 C,T=Q.shape
 if grammar=='none':return np.zeros((C,T),np.int32),1
 td=np.zeros((C,T),np.int16);td[:,2:]=s3(Q[:,1:-1]-Q[:,:-2])
 sd=np.zeros((C,T),np.int16);sd[2:,:]=s3(Q[1:-1,:]-Q[:-2,:])
 if grammar=='slopes9':return (td*3+sd).astype(np.int32),9
 pd=np.ones((C,T),np.int16);pd[:,1:]=s3(D[:,:-1])
 base=(td*9+sd*3+pd).astype(np.int32)
 if grammar=='slopes_prev27':return base,27
 band=(np.arange(C,dtype=np.int32)*4//C)[:,None]
 return (base*4+band).astype(np.int32),108

def fit_bias(D,ctx,nctx):
 b=np.zeros(nctx,np.int16);flatD=D.ravel();flatC=ctx.ravel()
 for k in range(nctx):
  v=flatD[flatC==k]
  if v.size==0:continue
  vv=v[(v>=-BIAS_LIM)&(v<=BIAS_LIM)]
  if vv.size:
   h=np.bincount((vv+BIAS_LIM).astype(np.int32),minlength=2*BIAS_LIM+1);b[k]=int(np.argmax(h))-BIAS_LIM
 return b

def invert(E,bias,grammar,Qshape,dt,dc,co,it):
 C,T=Qshape;Q=np.empty(Qshape,np.int32);D=np.empty(Qshape,np.int32)
 for t in range(T):
  for c in range(C):
   if grammar=='none':cx=0
   else:
    td=1
    if t>=2:
     z=int(Q[c,t-1])-int(Q[c,t-2]);td=0 if z<0 else (2 if z>0 else 1)
    sd=1
    if c>=2:
     z=int(Q[c-1,t])-int(Q[c-2,t]);sd=0 if z<0 else (2 if z>0 else 1)
    if grammar=='slopes9':cx=td*3+sd
    else:
     pd=1
     if t>=1:
      z=int(D[c,t-1]);pd=0 if z<0 else (2 if z>0 else 1)
     base=td*9+sd*3+pd
     cx=base if grammar=='slopes_prev27' else base*4+(c*4//C)
   dv=int(E[c,t])+int(bias[cx]);D[c,t]=dv;Q[c,t]=g._pred(Q,c,t,dt,dc,co,it,g.SCALE)+dv
 return D,Q

def main(path):
 with h5py.File(path,'r') as hf:
  d=hf['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,q.f.C0:q.f.C0+q.C],np.float64).T
 h,Q,D,dt,dc,co,it,changes,meanlegal=q.build_full(X,eps);mb,mrep,ddt,ddc,dco,dit=g.model_frame(dt,dc,co,it)
 screens=[];states={}
 for gr in GRAMMARS:
  ctx,nctx=contexts(Q,D,gr);bias=fit_bias(D,ctx,nctx);E=(D-bias[ctx]).astype(np.int32);table_bytes=2*nctx+2
  for W in q.WINDOWS:
   bb,nb=q.encode_zsm(E,W,q.SCREEN);score=int(mb)+table_bytes+len(bb);r={'grammar':gr,'nctx':nctx,'table_bytes':table_bytes,'W':int(W),'screen_total':score,'screen_payload':len(bb),'screen_bits':int(nb),'bias_nonzero':int(np.count_nonzero(bias)),'zero_fraction':float(np.mean(E[:,:q.SCREEN]==0))};screens.append(r);print(json.dumps({'screen':r}),flush=True)
  states[gr]=(E,bias,table_bytes)
 screens.sort(key=lambda r:r['screen_total']);finalists=[]
 for r in screens:
  key=(r['grammar'],r['W'])
  if key not in finalists:finalists.append(key)
  if len(finalists)>=3:break
 full=[]
 for gr,W in finalists:
  E,bias,tb=states[gr];bb,nb=q.encode_zsm(E,W,q.NT);Ed=q.decode_zsm(bb,nb,W,E.shape)
  if not np.array_equal(Ed,E):raise RuntimeError(('E decode',gr,W))
  Dd,Qd=invert(Ed,bias,gr,Q.shape,ddt,ddc,dco,dit)
  if not np.array_equal(Dd,D) or not np.array_equal(Qd,Q):raise RuntimeError(('modal replay',gr,W))
  me=float(np.max(np.abs(X-Qd.astype(np.float64)*h)))
  if me>eps*(1+5e-6):raise RuntimeError(('hard',me,eps))
  total=int(mb)+tb+len(bb)+q.HEADER+2;r={'grammar':gr,'W':W,'bytes':total,'model_bytes':int(mb),'table_bytes':tb,'payload_bytes':len(bb),'arithmetic_bits':int(nb),'maxerr':me,'zero_fraction':float(np.mean(E==0)),'bias_nonzero':int(np.count_nonzero(bias))};full.append(r);print(json.dumps({'full':r}),flush=True)
 full.sort(key=lambda r:r['bytes']);best=full[0];hist=2478995;old=2486110;bestbytes=min(old,best['bytes']);out={'screens':screens,'finalists':finalists,'full':full,'best_new':best,'best_learned_bytes':bestbytes,'historical_learned_bytes':old,'historical_ar32_zsm_bytes':hist,'gain_vs_historical_ar32_zsm':hist/bestbytes,'scope':'Charged causal modal-bias generator correction on the complete 128x30000 hard block. Starting from the exact PR551 near-2epsilon Q/model/defect field, fixed public causal context grammars use only already-decoded Q slopes, prior defect sign and optionally public channel band. For each context the encoder transmits an int16 modal defect bias; transformed defect E=D-bias(context) is exact. Grammar/W are prefix-screened, selector and full bias table bytes are charged, exactly one full ZSM stream is decoded, then D and Q are causally regenerated and hard-error validated. No bias or search path is free. A separate strongest-to-strongest AR32 audit is required before any win claim if this beats the historical incumbent.'};json.dump(out,open('imperial_near2eps_modal_bias_zsm.json','w'),indent=2);print(json.dumps({'summary':{'learned':bestbytes,'ar32_zsm':hist,'gain':hist/bestbytes,'best_new':best}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
