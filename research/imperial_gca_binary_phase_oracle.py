import json, math, struct, sys
import h5py
import numpy as np
import zstandard as zstd
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as ah
import imperial_huber_ar32_component_zsm_gps as cg

C=128;NT=30000;C0=512;STEP=267;RAD=133;INC=2468803;TARGET=2767977/2
CONFIGS={'zero':('base',64),'sign':('richall',4),'pref':('richmag',4),'suff':('richmag',4)}


def h0(a):
    _,n=np.unique(np.asarray(a).reshape(-1),return_counts=True);p=n/n.sum();return float(-(p*np.log2(p)).sum())

def gamma_cost(k):
    a=np.abs(np.asarray(k,dtype=np.int64));z=np.ones(a.shape,np.float64);nz=a>0
    if np.any(nz):z[nz]+=2+2*np.floor(np.log2(a[nz]))
    return z

def encode_k(K):
    payload=0;rows={}
    for comp in cg.COMPONENTS:
        gr,W=CONFIGS[comp];bb,nb=cg.encode_component(K,comp,W,NT,gr);payload+=len(bb)+13;rows[comp]={'payload_bytes':len(bb),'bits':int(nb),'grammar':gr,'W':W}
    return payload,rows

def bit_context_stats(B,K0):
    # Physical-ish upper diagnostics: H(B), H(B|prev B), H(B|channel group, clipped prev K, left sign).
    B=np.asarray(B,np.uint8);rows={'h0':h0(B)}
    x=B[:,1:].reshape(-1);p=B[:,:-1].reshape(-1);joint=(p.astype(np.uint16)<<1)|x;rows['h_given_prevB']=h0(joint)-h0(p)
    counts={}
    for c in range(C):
      g=c//16
      for t in range(NT):
        pk=int(K0[c,t-1]) if t else 0;pk=max(-4,min(4,pk))+4;left=int(K0[c-1,t]) if c else 0;ls=0 if left<0 else (2 if left>0 else 1);ctx=(g*9+pk)*3+ls;b=int(B[c,t]);counts.setdefault(ctx,[0,0])[b]+=1
    num=0.0;den=B.size
    for n0,n1 in counts.values():
      n=n0+n1
      if n0:num-=n0*math.log2(n0/n)
      if n1:num-=n1*math.log2(n1/n)
    rows['h_given_gpl']=num/den;rows['gpl_contexts']=len(counts)
    return rows

def main(path):
    with h5py.File(path,'r') as hf:
      d=hf['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,C0:C0+C],np.float64).T
    _,co=ah.fits(X);model,cod=cg.model_frame(co);R0,K0=ah.run_ar(X,cod);P=R0.astype(np.int64)-STEP*K0.astype(np.int64);Xi=np.rint(X).astype(np.int64);E=Xi-P
    flo=np.floor_divide(E,STEP);cei=flo+1
    vf=np.abs(E-STEP*flo)<=266;vc=np.abs(E-STEP*cei)<=266
    if not np.all(vf|vc):raise RuntimeError('no oracle choice')
    cf=gamma_cost(flo);cc=gamma_cost(cei)
    # Choose lower surrogate address cost; deterministic tie keeps the baseline-nearer sign stable.
    choose_ceil=vc & (~vf | (cc<cf))
    K=np.where(choose_ceil,cei,flo).astype(np.int32)
    D=np.where(choose_ceil,-RAD,RAD).astype(np.int16)
    R=(P+D.astype(np.int64)+STEP*K.astype(np.int64)).astype(np.int32)
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('hard',me,eps))
    kbytes,krows=encode_k(K);basebytes,baserows=encode_k(K0)
    bits=choose_ceil.astype(np.uint8);packed=np.packbits(bits.reshape(-1));zchoice=len(zstd.ZstdCompressor(level=19).compress(packed.tobytes()))
    st=bit_context_stats(bits,K0)
    # K-only oracle excludes phase side information on purpose. The naive-real column adds raw packed choice bits.
    framing=34+len(model)
    k_total=framing+kbytes
    raw_choice_total=k_total+len(packed)
    zstd_choice_total=k_total+zchoice
    n=C*NT
    out={'shape':[C,NT],'samples':n,'eps':eps,'maxerr':me,'incumbent_bytes':INC,'target_2x_bytes':TARGET,'baseline_reencoded_bytes':framing+basebytes,'oracle_k_only_bytes':k_total,'oracle_k_only_bps':8*k_total/n,'oracle_k_only_delta_vs_incumbent':k_total-INC,'choice_fraction_ceil':float(bits.mean()),'choice_h0_bps':st['h0'],'choice_context_diagnostics':st,'choice_raw_packed_bytes':len(packed),'choice_zstd_bytes':zchoice,'oracle_k_plus_raw_choice_bytes':raw_choice_total,'oracle_k_plus_zstd_choice_bytes':zstd_choice_total,'component_rows':krows,'baseline_component_rows':baserows,'scope':'Oracle headroom audit, NOT a codec claim for K-only bytes. At each sample, source-aware oracle chooses between floor lattice address with public phase +133 and ceiling address with phase -133, both guaranteed legal whenever selected. K is physically encoded with frozen incumbent component coders. The phase choice field is separately measured raw, zstd, and by conditional entropy. K-only bytes omit the source-dependent phase field and therefore are an optimistic ceiling; K+choice totals show simple explicit-side-information costs.'}
    json.dump(out,open('imperial_gca_binary_phase_oracle.json','w'),indent=2);print(json.dumps({'summary':out},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
