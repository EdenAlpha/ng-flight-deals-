import json,sys
import h5py,numpy as np,zstandard as zstd
import imperial_huber_ar32_coldstart_arithmetic_regions as a

REGIONS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
C=128;NT=8192;TB=1024;MODEL_BYTES=177
THRESH=(1,2,3,4,7,15,31)
Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor()

def backend_stream(K):
 total=0;reps={};frames=[];Kd=np.empty_like(K)
 for t0 in range(0,NT,TB):
  t1=min(NT,t0+TB);n,rep,q=a.m.encode_k(K[:,t0:t1]);n=int(n)+20;total+=n;Kd[:,t0:t1]=q;reps[rep]=reps.get(rep,0)+1;frames.append({'t0':t0,'bytes':n,'rep':rep})
 if not np.array_equal(Kd,K):raise RuntimeError('stream decode')
 return total,reps,frames,Kd

def sparse_tail(Dv):
 # Explicit alternative to encode_k: compressed binary mask plus packed signed tail values.
 mask=(Dv!=0).astype(np.uint8).ravel(order='C');mb=Z.compress(np.packbits(mask,bitorder='little').tobytes())
 vals=Dv.ravel(order='C')[mask.astype(bool)].astype('<i4');vb=Z.compress(vals.tobytes())
 # byte decode both components
 md=np.unpackbits(np.frombuffer(Zstd_decompress(mb),np.uint8),bitorder='little')[:mask.size]
 vd=np.frombuffer(Zstd_decompress(vb),'<i4')
 out=np.zeros(mask.size,np.int32);out[md.astype(bool)]=vd
 out=out.reshape(Dv.shape)
 if not np.array_equal(out,Dv):raise RuntimeError('sparse tail decode')
 return len(mb)+len(vb)+48,{'mask_bytes':len(mb),'value_bytes':len(vb),'nnz':int(vals.size),'nnz_fraction':float(vals.size/Dv.size)}

def Zstd_decompress(x):return D.decompress(x)

def main(path):
 a.NT=NT
 with h5py.File(path,'r') as f:
  ds=f['Acoustic'];_,gstd=a.m.stats(ds);eps=.1*gstd;rows=[]
  for region,c0 in REGIONS:
   X=np.asarray(ds[:NT,c0:c0+C],np.float64).T;_,hu=a.fits(X);R,K=a.run_ar(X,hu);me=float(np.max(np.abs(X-R.astype(np.float64))))
   if me>eps*(1+1e-12):raise RuntimeError((region,'hard',me,eps))
   base_payload,brep,_,Kb=backend_stream(K);base=MODEL_BYTES+base_payload
   arith,nbit,nb,Ka=a.arithmetic(K)
   if not np.array_equal(Ka,K):raise RuntimeError((region,'arith K'))
   cand=[]
   for T in THRESH:
    core=np.clip(K,-T,T).astype(np.int32);tail=(K-core).astype(np.int32)
    cb,crep,_,cd=backend_stream(core);tb,trep,_,td=backend_stream(tail)
    if not np.array_equal(cd+td,K):raise RuntimeError((region,T,'sum decode'))
    both=MODEL_BYTES+cb+tb+24
    # Also test a literal sparse tail container; core stays self-decoding encode_k.
    mask=(tail!=0).astype(np.uint8).ravel(order='C');mb=Z.compress(np.packbits(mask,bitorder='little').tobytes());vals=tail.ravel(order='C')[mask.astype(bool)].astype('<i4');vb=Z.compress(vals.tobytes())
    md=np.unpackbits(np.frombuffer(D.decompress(mb),np.uint8),bitorder='little')[:mask.size];vd=np.frombuffer(D.decompress(vb),'<i4');td2=np.zeros(mask.size,np.int32);td2[md.astype(bool)]=vd;td2=td2.reshape(tail.shape)
    if not np.array_equal(td2,tail):raise RuntimeError((region,T,'mask decode'))
    sparse=MODEL_BYTES+cb+len(mb)+len(vb)+64
    cand.append({'threshold':T,'core_nnz_fraction':float(np.mean(core!=0)),'tail_nnz_fraction':float(np.mean(tail!=0)),
                 'core_bytes':cb,'tail_backend_bytes':tb,'tail_mask_bytes':len(mb),'tail_value_bytes':len(vb),
                 'split_backend_bytes':both,'split_backend_bps':8*both/X.size,'gain_split_vs_huber_backend':base/both,
                 'sparse_tail_bytes':sparse,'sparse_tail_bps':8*sparse/X.size,'gain_sparse_vs_huber_backend':base/sparse,
                 'core_reps':crep,'tail_reps':trep})
   cand.sort(key=lambda q:min(q['split_backend_bytes'],q['sparse_tail_bytes']))
   best=cand[0];bestbytes=min(best['split_backend_bytes'],best['sparse_tail_bytes']);bestmode='split_backend' if best['split_backend_bytes']<=best['sparse_tail_bytes'] else 'sparse_tail'
   sz=0
   for t0 in range(0,NT,TB):b,_=a.m.szrun(X[:,t0:min(t0+TB,NT)],eps);sz+=b
   row={'region':region,'c0':c0,'samples':int(X.size),'sz3_bytes':sz,'sz3_bps':8*sz/X.size,
        'huber_backend':{'bytes':base,'bps':8*base/X.size,'gain_vs_sz3':sz/base,'reps':brep},
        'huber_arithmetic':{'bytes':arith,'bps':8*arith/X.size,'gain_vs_sz3':sz/arith,'arithmetic_bits':nbit,'symbol_bits':nb},
        'best':{'threshold':best['threshold'],'mode':bestmode,'bytes':bestbytes,'bps':8*bestbytes/X.size,'gain_vs_huber_backend':base/bestbytes,'gain_vs_huber_arithmetic':arith/bestbytes,'gain_vs_sz3':sz/bestbytes},
        'candidates':cand,'maxerr':me,'k_abs_quantiles':{str(q):float(np.quantile(np.abs(K),q)) for q in (0.5,0.9,0.95,0.99,0.999)},
        'tail_fractions':{str(T):float(np.mean(np.abs(K)>T)) for T in THRESH}}
   rows.append(row);print(json.dumps(row,indent=2),flush=True)
  out={'global_std':gstd,'eps':eps,'thresholds':list(THRESH),'rows':rows,
       'scope':'Exact factorization gate motivated by PR #369 heavy-tailed decoder-real innovations (hard excess kurtosis ~12). The real prefix-only Huber267 AR32 K is unchanged. For each threshold T, K is decomposed exactly as core=clip(K,-T,T) plus sparse tail=K-core. Core and tail are first independently byte-decoded through the incumbent representation menu with all separate frame overhead charged. A second real tail container sends a Zstd-compressed binary tail mask plus compressed int32 nonzero tail values; mask and values are byte-decoded and exact K is reconstructed. The ordinary Huber backend and PR #402 cold-start arithmetic are rerun as controls, along with matched SZ3 and source hard-error verification. This asks whether rare coherent/high-magnitude innovations are being penalized by sharing global bitplanes with the dense core; it is not an entropy oracle. No AI. Draft/do not merge.'}
  json.dump(out,open('imperial_huber_ar32_core_tail_split.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
