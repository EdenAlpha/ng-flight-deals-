import json,sys
import h5py,numpy as np
import imperial_near2eps_learned_zsm_fullhard as q
import imperial_near2eps_scale_128x4096 as sc
import imperial_huber_ar32_coldstart_arithmetic_regions as ah
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m
q.f.q_decode=sc.q_decode
C=128;NT=30000;SCREEN=4096;WINDOWS=(4,8,64)
GRAMMARS=('base','richmag','richall')

def mbin(x):
 x=abs(int(x));return 0 if x==0 else (1 if x==1 else (2 if x==2 else (3 if x<=4 else (4 if x<=8 else 5))))
def scat(x):x=int(x);return 0 if x<0 else (2 if x>0 else 1)
def clip4(x):return int(max(-4,min(4,int(x))))+4

def layout(grammar):
 if grammar=='base':return None
 if grammar=='richmag':
  nz=9*9*6;ns=3*3*6;npf=6*6*6*16;nsf=16*16*6*6
 elif grammar=='richall':
  nz=9*9*3*6;ns=3*3*3*6;npf=6*6*3*6*16;nsf=16*16*6*6*6
 else:raise ValueError(grammar)
 return (0,nz,nz+ns,nz+ns+npf,nz+ns+npf+nsf)

def ctxs(grammar,prev,left,diag,ac,qmag=None,pos=None,kind='zero'):
 if grammar=='base':
  if kind=='zero':return q.zero_ctx(prev,left,ac)
  if kind=='sign':return q.sign_ctx(prev,left,ac)
  if kind=='pref':return q.pref_ctx(prev,ac,pos)
  return q.suff_ctx(qmag,pos,ac)
 o0,o1,o2,o3,n=layout(grammar)
 if grammar=='richmag':
  if kind=='zero':return (clip4(prev)*9+clip4(left))*6+ac
  if kind=='sign':return o1+(scat(prev)*3+scat(left))*6+ac
  if kind=='pref':return o2+(((mbin(prev)*6+mbin(left))*6+ac)*16+min(pos,15))
  return o3+(((min(qmag,15)*16+min(pos,15))*6+mbin(prev))*6+ac)
 if kind=='zero':return ((clip4(prev)*9+clip4(left))*3+scat(diag))*6+ac
 if kind=='sign':return o1+((scat(prev)*3+scat(left))*3+scat(diag))*6+ac
 if kind=='pref':return o2+((((mbin(prev)*6+mbin(left))*3+mbin(diag))*6+ac)*16+min(pos,15))
 return o3+((((min(qmag,15)*16+min(pos,15))*6+mbin(prev))*6+mbin(left))*6+ac)

def encode(K,W,nt,grammar):
 if grammar=='base':return q.encode_zsm(K,W,nt)
 nctx=layout(grammar)[-1];E=q.AE(nctx);ring=np.zeros((C,W),np.int32);sums=np.zeros(C,np.int64)
 for t in range(nt):
  rp=t%W;cnt=min(t,W)
  for c in range(C):
   ac=q.ac_state(sums[c],cnt);prev=int(K[c,t-1]) if t else 0;left=int(K[c-1,t]) if c else 0;diag=int(K[c-1,t-1]) if c and t else 0;k=int(K[c,t])
   iz=1 if k==0 else 0;E.put(iz,ctxs(grammar,prev,left,diag,ac,kind='zero'))
   if not iz:
    E.put(1 if k<0 else 0,ctxs(grammar,prev,left,diag,ac,kind='sign'));mag=abs(k);qq=mag.bit_length()-1
    for j in range(qq):E.put(0,ctxs(grammar,prev,left,diag,ac,pos=j,kind='pref'))
    E.put(1,ctxs(grammar,prev,left,diag,ac,pos=qq,kind='pref'));rem=mag-(1<<qq)
    for bp in range(qq-1,-1,-1):E.put((rem>>bp)&1,ctxs(grammar,prev,left,diag,ac,qmag=qq,pos=qq-1-bp,kind='suff'))
   old=int(ring[c,rp]);new=abs(k);ring[c,rp]=new;sums[c]+=new-old
 return E.finish()

def decode(bb,nbit,W,shape,grammar):
 if grammar=='base':return q.decode_zsm(bb,nbit,W,shape)
 nctx=layout(grammar)[-1];D=q.AD(bb,nbit,nctx);K=np.zeros(shape,np.int32);ring=np.zeros((C,W),np.int32);sums=np.zeros(C,np.int64)
 for t in range(shape[1]):
  rp=t%W;cnt=min(t,W)
  for c in range(C):
   ac=q.ac_state(sums[c],cnt);prev=int(K[c,t-1]) if t else 0;left=int(K[c-1,t]) if c else 0;diag=int(K[c-1,t-1]) if c and t else 0;iz=D.get(ctxs(grammar,prev,left,diag,ac,kind='zero'))
   if iz:k=0
   else:
    neg=D.get(ctxs(grammar,prev,left,diag,ac,kind='sign'));qq=0
    while True:
     b=D.get(ctxs(grammar,prev,left,diag,ac,pos=qq,kind='pref'))
     if b:break
     qq+=1
     if qq>30:raise RuntimeError('gamma overflow')
    rem=0
    for pos in range(qq):rem=(rem<<1)|D.get(ctxs(grammar,prev,left,diag,ac,qmag=qq,pos=pos,kind='suff'))
    mag=(1<<qq)+rem;k=-mag if neg else mag
   K[c,t]=k;old=int(ring[c,rp]);new=abs(k);ring[c,rp]=new;sums[c]+=new-old
 return K

def choose(K,label):
 rows=[]
 for gr in GRAMMARS:
  for W in WINDOWS:
   bb,nb=encode(K,W,SCREEN,gr);r={'stream':label,'grammar':gr,'W':W,'prefix_bytes':len(bb),'prefix_bits':int(nb)};rows.append(r);print(json.dumps(r),flush=True)
 rows.sort(key=lambda z:z['prefix_bytes']);return rows[0],rows

def main(path):
 with h5py.File(path,'r') as hf:
  d=hf['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,q.f.C0:q.f.C0+C],np.float64).T
 h,Q,D,dt,dc,co,it,changes,meanlegal=q.build_full(X,eps);mb,mrep,ddt,ddc,dco,dit=g.model_frame(dt,dc,co,it)
 _,aco=ah.fits(X);R,K=ah.run_ar(X,aco)
 lb,lrows=choose(D,'learned');ab,arows=choose(K,'ar32')
 full=[]
 for label,A,best in [('learned',D,lb),('ar32',K,ab)]:
  gr=best['grammar'];W=best['W'];bb,nb=encode(A,W,NT,gr);Ad=decode(bb,nb,W,A.shape,gr)
  if not np.array_equal(Ad,A):raise RuntimeError((label,'decode'))
  if label=='learned':
   Qd=q.f.q_decode(Ad,ddt,ddc,dco,dit,q.f.SCALE)
   if not np.array_equal(Qd,Q):raise RuntimeError('learned Q replay')
   me=float(np.max(np.abs(X-Qd.astype(np.float64)*h)));total=int(mb)+len(bb)+q.HEADER+2
  else:
   Rd=ah.decode_source(Ad,aco)
   if not np.array_equal(Rd,R):raise RuntimeError('AR replay')
   me=float(np.max(np.abs(X-Rd.astype(np.float64))));total=len(bb)+ah.MODEL_BYTES+34
  if me>eps*(1+5e-6):raise RuntimeError((label,'hard',me,eps))
  full.append({'stream':label,'grammar':gr,'W':W,'payload_bytes':len(bb),'bits':int(nb),'total_bytes':int(total),'maxerr':me})
 hist=2478995;learned0=2486110
 learned=min([r for r in full if r['stream']=='learned'][0]['total_bytes'],learned0)
 ar=min([r for r in full if r['stream']=='ar32'][0]['total_bytes'],hist)
 out={'full':full,'learned_best_bytes':learned,'ar32_best_bytes':ar,'gain_learned_vs_ar32':ar/learned,'historical_learned_bytes':learned0,'historical_ar32_zsm_bytes':hist,'prefix_screens':lrows+arows,'scope':'Fair strongest-to-strongest ZSM context search on the identical full 128x30000 hard block. A fixed public grammar menu (historical base, richer magnitude context, richer diagonal+magnitude context) and W=4/8/64 is prefix-screened independently for both the learned near-2epsilon defect and historical Huber AR32 innovation streams. Each new-menu stream charges one grammar byte plus one window byte. Exactly one full candidate per representation is materialized and independently decoded/replayed under the unchanged hard error. Final strongest bytes are min(new-menu stream, each representation historical baseline), so a generic entropy improvement is granted equally to AR32 before any victory claim.'};json.dump(out,open('imperial_fair_zsm_context_search.json','w'),indent=2);print(json.dumps({'summary':{'learned':learned,'ar32':ar,'gain':ar/learned,'full':full}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
