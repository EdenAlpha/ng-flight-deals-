import json,sys
import h5py,numpy as np,zstandard as zstd
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as h

C=128;NT=4096;TRAIN=1024;TB=1024;REGIONS=(('hard',512),('easy',2304));LENS=(4,8,16);MS=(16,64,256)
Z=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()

def h0(a):
 _,n=np.unique(np.asarray(a).ravel(),return_counts=True);p=n/n.sum();return float(-(p*np.log2(p)).sum())

def zpack(a):return Z.compress(np.ascontiguousarray(a).tobytes())

def variant(K,co,L,M):
 nb=NT//L;B=K.reshape(C,nb,L);flat=B.reshape(-1,L)
 if int(flat.min())<-32768 or int(flat.max())>32767:raise RuntimeError(('K int16',flat.min(),flat.max()))
 uniq,inv,cnt=np.unique(flat.astype(np.int16),axis=0,return_inverse=True,return_counts=True);order=np.argsort(cnt)[::-1];mm=min(int(M),len(uniq));chosen=order[:mm];rank=np.full(len(uniq),-1,np.int32);rank[chosen]=np.arange(mm,dtype=np.int32);rid=rank[inv];escmask=rid<0;ids=np.where(escmask,mm,rid).astype(np.int32).reshape(C,nb);esc=flat[escmask].astype(np.int16);DIC=uniq[chosen].astype(np.int16)
 dblob=zpack(DIC.astype('<i2'));eblob=zpack(esc.astype('<i2'))
 old=h.NT;h.NT=nb
 ab,nbit,nbits,Id=h.arithmetic(ids)
 h.NT=old
 izc=zpack(ids.astype('<u2'));izt=zpack(ids.T.astype('<u2'));methods=[('arithmetic',int(ab)),('zstd_channel',len(izc)+h.MODEL_BYTES+16),('zstd_time',len(izt)+h.MODEL_BYTES+16)];method,idbytes=min(methods,key=lambda x:x[1]);total=int(idbytes)+len(dblob)+len(eblob)+48
 dd=np.frombuffer(ZD.decompress(dblob),'<i2').reshape(mm,L).astype(np.int32) if mm else np.empty((0,L),np.int32);ed=np.frombuffer(ZD.decompress(eblob),'<i2').reshape(-1,L).astype(np.int32)
 if method=='arithmetic':
  if not np.array_equal(Id,ids):
   raise RuntimeError(('id arithmetic',L,M))
  ID=Id
 elif method=='zstd_channel':ID=np.frombuffer(ZD.decompress(izc),'<u2').reshape(C,nb).astype(np.int32)
 else:ID=np.frombuffer(ZD.decompress(izt),'<u2').reshape(nb,C).T.astype(np.int32)
 if not np.array_equal(ID,ids):raise RuntimeError(('id decode',L,M,method))
 out=np.empty_like(B,dtype=np.int32);ep=0
 for c in range(C):
  for q in range(nb):
   x=int(ID[c,q])
   if x<mm:
    out[c,q]=dd[x]
   elif x==mm:
    if ep>=len(ed):
     raise RuntimeError(('escape eof',L,M))
    out[c,q]=ed[ep]
    ep+=1
   else:raise RuntimeError(('bad id',x,mm))
 if ep!=len(ed):raise RuntimeError(('escape tail',ep,len(ed)))
 Kd=out.reshape(C,NT)
 if not np.array_equal(Kd,K):raise RuntimeError(('K motif decode',L,M))
 R=h.decode_source(Kd,co)
 return {'L':L,'M_requested':M,'M_actual':mm,'bytes':total,'bps':8*total/K.size,'id_method':method,'id_bytes':int(idbytes),'dictionary_bytes':len(dblob),'escape_bytes':len(eblob),'unique_patterns':int(len(uniq)),'dictionary_hit_fraction':float(1-np.mean(escmask)),'escape_blocks':int(np.count_nonzero(escmask)),'blocks':int(len(flat)),'id_h0_bits_per_block':h0(ids),'ideal_block_entropy_bps':h0(inv.reshape(C,nb))/L,'maxerr':None},R

def main(path):
 h.C=C;h.NT=NT;h.TRAIN=TRAIN
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
  for region,c0 in REGIONS:
   X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,co=h.fits(X);R,K=h.run_ar(X,co);base,n0,nb0,D0=h.arithmetic(K);RR=h.decode_source(D0,co);me0=float(np.max(np.abs(X-RR.astype(np.float64))))
   if me0>eps*(1+1e-12):raise RuntimeError((region,'base hard',me0,eps))
   sz=0
   for t0 in range(0,NT,TB):q,_=m.szrun(X[:,t0:t0+TB],eps);sz+=int(q)
   vv=[]
   for L in LENS:
    for M in MS:
     r,Rd=variant(K,co,L,M);me=float(np.max(np.abs(X-Rd.astype(np.float64))))
     if me>eps*(1+1e-12):raise RuntimeError((region,L,M,'hard',me,eps))
     r['maxerr']=me;r.update({'gain_vs_step267':base/r['bytes'],'gain_vs_sz3':sz/r['bytes'],'ratio_to_2x_target':r['bytes']/(sz/2)});vv.append(r);print(json.dumps({'region':region,'variant':r},indent=2),flush=True)
   best=min(vv,key=lambda z:z['bytes']);row={'region':region,'c0':c0,'samples':int(X.size),'eps':eps,'step267_bytes':int(base),'step267_bps':8*base/X.size,'sz3_bytes':sz,'sz3_bps':8*sz/X.size,'best':best,'variants':vv};rows.append(row);print(json.dumps({'summary':row},indent=2),flush=True)
  out={'global_std':gstd,'eps':eps,'shape':[C,NT],'lengths':list(LENS),'dictionary_sizes':list(MS),'rows':rows,'scope':'Exact post-AR motif dictionary pilot on hard/easy Imperial. The incumbent Huber AR32 step267 K field is unchanged, so reconstruction and fidelity are exactly the incumbent. Each channel is split into nonoverlapping K blocks of length 4/8/16. A source-trained dictionary of the M most frequent exact K blocks is transmitted explicitly as Zstd-compressed int16 patterns; every block becomes a dictionary ID or an escape ID plus exact int16 escape block. ID streams test the incumbent exact adaptive arithmetic backend and two deterministic Zstd layouts; dictionary, escapes, shared AR model and framing are all charged. The top-level decoder reconstructs every ID, dictionary pattern and escape, recovers the exact K field, regenerates the source and hard-error checks it. This is a strict screen for vector/motif redundancy beyond previous-K contexts before any approximate VQ+repair experiment. No AI. Draft/do not merge.'};json.dump(out,open('imperial_ar32_exact_motif_dictionary.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])