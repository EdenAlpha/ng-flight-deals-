import json,sys,os,math
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import h5py,numpy as np,zstandard as zstd
from research.imperial_spacetime_control_mesh import stats,szrun,rep2
C=128;T=1024;SAFETY=1-1e-5;PHASES=4
MODS=(2,3,4,5,8,16);WEIGHTS=(0.0,0.25,0.5,1.0);Z=zstd.ZstdCompressor(level=19)
def zlen(a):return len(Z.compress(np.ascontiguousarray(a).tobytes()))
def residue_bytes(r,M):
 r=np.asarray(r,np.uint8).ravel();best=zlen(r)+24;bits=int(math.ceil(math.log2(M)));acc=nb=0;out=bytearray()
 for v in r:
  acc|=int(v)<<nb;nb+=bits
  while nb>=8:out.append(acc&255);acc>>=8;nb-=8
 if nb:out.append(acc&255)
 return min(best,len(Z.compress(bytes(out)))+32)
def escape_bytes(dq):
 dq=np.asarray(dq,np.int32).ravel();nz=dq!=0;sup=zlen(np.packbits(nz.astype(np.uint8),bitorder='little'));v=dq[nz]
 if not len(v):return sup+32,0.0
 mn,mx=int(v.min()),int(v.max())
 for dt in (np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4')):
  if mn>=np.iinfo(dt).min and mx<=np.iinfo(dt).max:return sup+zlen(v.astype(dt))+48,float(nz.mean())
def H(a):
 _,c=np.unique(a,return_counts=True);p=c/c.sum();return float(-(p*np.log2(p)).sum())
def views(P,mask):
 ps=[];pt=[];pm=[]
 for c,t in np.argwhere(~mask):
  sv=[];tv=[];av=[]
  for cc in (c-1,c+1):
   if 0<=cc<C:sv.append(P[cc,t]);av.append(P[cc,t])
  for tt in (t-1,t+1):
   if 0<=tt<T:tv.append(P[c,tt]);av.append(P[c,tt])
  ps.append(np.mean(sv) if sv else np.mean(tv));pt.append(np.mean(tv) if tv else np.mean(sv));pm.append(np.median(av))
 return np.asarray(ps),np.asarray(pt),np.asarray(pm)
def unwrap(r,M,kest):return r.astype(np.int64)+M*np.rint((kest-r)/M).astype(np.int64)
def run(X,bound,ph,demod,w,M,side):
 s=np.ones(T) if not demod else np.where(np.arange(T)%2==0,1.,-1.);Y=X*s[None,:];step=2*bound;phi=step*ph/PHASES;cc=np.arange(C)[:,None];tt=np.arange(T)[None,:];mask=((cc+tt)&1)==0
 q=np.rint((Y[mask]-phi)/step).astype(np.int32);P=np.zeros_like(Y);P[mask]=phi+step*q;Ps,Pt,Pm=views(P,mask);base=Ps if w==0 else (Ps+w*Pt)/(1+w);sv={'spatial':Ps,'temporal':Pt,'median':Pm}[side];K=np.rint((Y[~mask]-base)/step).astype(np.int64);r=np.mod(K,M).astype(np.uint8);Kg=unwrap(r,M,(sv-base)/step);dq=((K-Kg)//M).astype(np.int32);Kd=Kg+M*dq.astype(np.int64)
 if not np.array_equal(K,Kd):raise RuntimeError('modulo decode mismatch')
 R=np.zeros_like(Y);R[mask]=P[mask];R[~mask]=base+step*Kd;R*=s[None,:];me=float(np.max(np.abs(X-R)))
 if me>bound/SAFETY*(1+5e-6):raise RuntimeError(('hard',me))
 A0=np.rint((Y[0::2,0::2]-phi)/step).astype(np.int32);A1=np.rint((Y[1::2,1::2]-phi)/step).astype(np.int32);cb=rep2(A0)[0]+rep2(A1)[0];rb=residue_bytes(r,M);eb,ef=escape_bytes(dq);return {'phase':ph,'demod':demod,'weight':w,'M':M,'side':side,'bytes':cb+rb+eb+160,'control_bytes':cb,'residue_bytes':rb,'escape_bytes':eb,'escape_fraction':ef,'residue_entropy':H(r),'maxerr':me}
def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,std=stats(d);eps=.1*std;b=eps*SAFETY;specs=[('early',0,3392),('center',14488,3392),('edge',14488,6784),('late',28976,3392)];rows=[];tiles=[]
  for name,t0,c0 in specs:
   X=np.asarray(d[t0:t0+T,c0:c0+C],np.float64).T;sb=szrun(X,eps);tiles.append((name,sb))
   for ph in range(PHASES):
    for dm in (False,True):
     for w in WEIGHTS:
      for M in MODS:
       for side in ('spatial','temporal','median'):
        r=run(X,b,ph,dm,w,M,side);r.update(tile=name,sz3_bytes=sb,gain_vs_sz3=sb/r['bytes'],bps=8*r['bytes']/X.size);rows.append(r)
  ss=sum(x[1] for x in tiles);defs=set((r['phase'],r['demod'],r['weight'],r['M'],r['side']) for r in rows);comb=[]
  for k in defs:
   rr=[r for r in rows if (r['phase'],r['demod'],r['weight'],r['M'],r['side'])==k];bb=sum(r['bytes'] for r in rr);comb.append({'phase':k[0],'demod':k[1],'weight':k[2],'M':k[3],'side':k[4],'bytes':bb,'gain_vs_sz3':ss/bb,'bps':8*bb/(C*T*len(rr)),'min_tile_gain':min(r['gain_vs_sz3'] for r in rr),'control_bytes':sum(r['control_bytes'] for r in rr),'residue_bytes':sum(r['residue_bytes'] for r in rr),'escape_bytes':sum(r['escape_bytes'] for r in rr),'median_escape_fraction':float(np.median([r['escape_fraction'] for r in rr])),'median_residue_entropy':float(np.median([r['residue_entropy'] for r in rr]))})
  comb.sort(key=lambda x:x['bytes']);out={'std':std,'eps':eps,'two_x_target_bps':1.6659195794753086,'parent_pr236_correction_bytes':87090,'combos':comb,'rows':rows,'scope':'Modulo-correction screen on PR236 checkerboard controls. The dense integer correction is replaced by residue K mod M; a second decoder-known view chooses the congruent lift, and a sparse exact quotient fixes wrong lifts. Residue/escape frames are fully charged; algebraic correction decoding and final hard error are verified. Control byte accounting is unchanged from PR236.'};print(json.dumps({'best':comb[:12]},indent=2),flush=True);json.dump(out,open('imperial_dualview_modulo_correction.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
