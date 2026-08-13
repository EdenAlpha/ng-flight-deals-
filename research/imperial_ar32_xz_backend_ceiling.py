import json,sys,lzma
import h5py,numpy as np
import imperial_ar32_maximal_legal_step as s
import imperial_decoder_phase_automaton as c
import imperial_dyadic_shared_resonator as ar
STEP=267

def dt(a):
 a=np.asarray(a,np.int32);mn,mx=int(a.min()),int(a.max());return np.dtype('i1') if mn>=-128 and mx<=127 else (np.dtype('<i2') if mn>=-32768 and mx<=32767 else np.dtype('<i4'))
def xz(raw):return lzma.compress(raw,format=lzma.FORMAT_XZ,preset=9|lzma.PRESET_EXTREME)
def unxz(b):return lzma.decompress(b,format=lzma.FORMAT_XZ)
def variants(K):
 K=np.asarray(K,np.int32);out=[]
 A={'raw':K.copy()};q=K.copy();q[:,1:]=K[:,1:]-K[:,:-1];A['dt']=q;q=K.copy();q[1:]=K[1:]-K[:-1];A['ds']=q
 for n,v in A.items():
  typ=dt(v);raw=v.astype(typ).tobytes();bb=xz(raw);r=np.frombuffer(unxz(bb),typ).astype(np.int32).reshape(v.shape)
  if n=='raw':back=r
  elif n=='dt':back=np.cumsum(r,axis=1,dtype=np.int32)
  else:back=np.cumsum(r,axis=0,dtype=np.int32)
  if not np.array_equal(back,K):raise RuntimeError(n)
  out.append((len(bb)+40,n+'_'+typ.str))
 return min(out)
def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,std=c.stats(d);eps=.1*std;rows=[]
  for name,c0 in s.SPECS:
   X=np.asarray(d[:s.NT,c0:c0+s.C],np.float64).T;co=ar.fit_shared(X[:,:s.TRAIN],s.P);mb,cd=ar.model_frame(co);R,K=s.recur(X,np.asarray(cd,np.float32),s.P,STEP)
   old=new=0;wins={}
   for t0 in range(0,s.NT,s.TB):
    k=K[:,t0:t0+s.TB];o=c.encode_k(k);old+=int(o[0])+20;x=variants(k)
    if x[0]<int(o[0])+20:new+=x[0];w=x[1]
    else:new+=int(o[0])+20;w='zstd:'+o[1]
    wins[w]=wins.get(w,0)+1
   total=int(mb)+new+32;oldtotal=int(mb)+old+32;sz=s.matched_sz3(X,eps);row={'region':name,'bytes':total,'bps':8*total/X.size,'old_bytes':oldtotal,'old_bps':8*oldtotal/X.size,'gain_vs_old':oldtotal/total,'gain_vs_sz3':sz/total,'wins':wins};rows.append(row);print(json.dumps(row),flush=True)
 n=s.C*s.NT*len(rows);tot=sum(r['bytes'] for r in rows);old=sum(r['old_bytes'] for r in rows);out={'aggregate':{'bytes':tot,'bps':8*tot/n,'old_bytes':old,'old_bps':8*old/n,'gain_vs_old':old/tot},'rows':rows,'scope':'Packaging-only ceiling: exact AR32 step267 K frames compare the incumbent self-decoding Zstd menu against XZ/LZMA2 preset9-extreme on raw, temporal-delta and spatial-delta integer representations. Every XZ stream is decoded and inverted exactly. No source-model or fidelity change, no AI.'};print(json.dumps(out['aggregate'],indent=2));json.dump(out,open('imperial_ar32_xz_backend_ceiling.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])