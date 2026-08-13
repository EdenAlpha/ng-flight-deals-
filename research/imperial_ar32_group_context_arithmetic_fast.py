import sys
import numpy as np
import imperial_ar32_channel_prev_arithmetic as a

MODES=('g16_prev4_left4','g32_prev4_left4','g16_prev4_leftsign','g8_prev4_leftsign','prev4_left4_diag4')

def nctx(mode,nb):
 if mode=='g16_prev4_left4':return (a.C//16)*9*9*nb*4
 if mode=='g32_prev4_left4':return (a.C//32)*9*9*nb*4
 if mode=='g16_prev4_leftsign':return (a.C//16)*9*3*nb*4
 if mode=='g8_prev4_leftsign':return (a.C//8)*9*3*nb*4
 if mode=='prev4_left4_diag4':return 9*9*9*nb*4
 raise ValueError(mode)

def ctxid(mode,c,prev,left,diag,bitpos,prefix2,nb):
 pv=a.clip4(prev);lv=a.clip4(left);dv=a.clip4(diag);ls=0 if left==0 else (1 if left>0 else 2)
 if mode=='g16_prev4_left4':base=((c//16)*9+pv)*9+lv
 elif mode=='g32_prev4_left4':base=((c//32)*9+pv)*9+lv
 elif mode=='g16_prev4_leftsign':base=((c//16)*9+pv)*3+ls
 elif mode=='g8_prev4_leftsign':base=((c//8)*9+pv)*3+ls
 elif mode=='prev4_left4_diag4':base=(pv*9+lv)*9+dv
 else:raise ValueError(mode)
 return ((base*nb+bitpos)*4+prefix2)

def seed_counts(Kprefix,mode,nb):
 counts=np.ones((nctx(mode,nb),2),np.int32);u=a.zig(Kprefix)
 for t in range(Kprefix.shape[1]):
  for c in range(a.C):
   prev=int(Kprefix[c,t-1]) if t>0 else 0;left=int(Kprefix[c-1,t]) if c>0 else 0;diag=int(Kprefix[c-1,t-1]) if c>0 and t>0 else 0;pref=0;val=int(u[c,t])
   for bp in range(nb-1,-1,-1):
    b=(val>>bp)&1;pos=nb-1-bp;cx=ctxid(mode,c,prev,left,diag,pos,pref,nb);counts[cx,b]+=1;pref=((pref<<1)|b)&3
 return counts

def arithmetic_heldout(K,mode,nb):
 init=seed_counts(K[:,:a.TRAIN],mode,nb);enc=a.AE(nctx(mode,nb),init);u=a.zig(K)
 for t in range(a.TRAIN,K.shape[1]):
  for c in range(a.C):
   prev=int(K[c,t-1]);left=int(K[c-1,t]) if c>0 else 0;diag=int(K[c-1,t-1]) if c>0 else 0;pref=0;val=int(u[c,t])
   for bp in range(nb-1,-1,-1):
    b=(val>>bp)&1;pos=nb-1-bp;cx=ctxid(mode,c,prev,left,diag,pos,pref,nb);enc.put(b,cx);pref=((pref<<1)|b)&3
 bb,nbit=enc.finish();Kd=np.zeros_like(K);Kd[:,:a.TRAIN]=K[:,:a.TRAIN];dec=a.AD(bb,nbit,nctx(mode,nb),init)
 for t in range(a.TRAIN,K.shape[1]):
  for c in range(a.C):
   prev=int(Kd[c,t-1]);left=int(Kd[c-1,t]) if c>0 else 0;diag=int(Kd[c-1,t-1]) if c>0 else 0;pref=0;val=0
   for bp in range(nb-1,-1,-1):
    pos=nb-1-bp;cx=ctxid(mode,c,prev,left,diag,pos,pref,nb);b=dec.get(cx);val=(val<<1)|b;pref=((pref<<1)|b)&3
   Kd[c,t]=int(a.unzig(np.asarray([val],np.uint64))[0])
 if not np.array_equal(Kd,K):raise RuntimeError(('group arithmetic decode',mode))
 return len(bb)+16,nbit,Kd

a.nctx=nctx
a.arithmetic_heldout=arithmetic_heldout
a.MODES=MODES
a.SPECS=(('hard',512),)
a.NT=4096
if __name__=='__main__':a.main(sys.argv[1])
