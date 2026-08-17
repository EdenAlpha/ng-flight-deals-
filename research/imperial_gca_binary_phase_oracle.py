import json, math, struct, sys
import h5py
import numpy as np
import zstandard as zstd
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as ah
import imperial_huber_ar32_component_zsm_gps as cg

C=128;NT=30000;C0=512;STEP=267;RAD=133;INC=2465652;TARGET=2767977/2
CONFIGS={'zero':('base',64),'sign':('richall',4),'pref':('richmag',4),'suff':('richmag',4)}


def h0(a):
    _,n=np.unique(np.asarray(a).reshape(-1),return_counts=True);p=n/n.sum();return float(-(p*np.log2(p)).sum())
def gcost(k):
    a=abs(int(k));return 1.0 if a==0 else 3.0+2.0*math.floor(math.log2(a))
def encode_k(K):
    stream=bytearray();entries={};rows={}
    for comp in cg.COMPONENTS:
        gr,W=CONFIGS[comp];bb,nb=cg.encode_component(K,comp,W,NT,gr);sid=cg.config_id(gr,W)
        stream.extend(struct.pack('<BQI',sid,int(nb),len(bb)));stream.extend(bb);entries[comp]=(sid,int(nb),bb)
        rows[comp]={'payload_bytes':len(bb),'bits':int(nb),'grammar':gr,'W':W}
    return bytes(stream),entries,rows
def bit_context_stats(B,K):
    B=np.asarray(B,np.uint8);rows={'h0':h0(B)}
    x=B[:,1:].reshape(-1);p=B[:,:-1].reshape(-1);joint=(p.astype(np.uint16)<<1)|x;rows['h_given_prevB']=h0(joint)-h0(p)
    counts={}
    for c in range(C):
      g=c//16
      for t in range(NT):
        pk=int(K[c,t-1]) if t else 0;pk=max(-4,min(4,pk))+4;left=int(K[c-1,t]) if c else 0;ls=0 if left<0 else (2 if left>0 else 1);ctx=(g*9+pk)*3+ls;b=int(B[c,t]);counts.setdefault(ctx,[0,0])[b]+=1
    num=0.0;den=B.size
    for n0,n1 in counts.values():
      n=n0+n1
      if n0:num-=n0*math.log2(n0/n)
      if n1:num-=n1*math.log2(n1/n)
    rows['h_given_gpl']=num/den;rows['gpl_contexts']=len(counts);return rows
def build_oracle(X,co):
    Xi=np.rint(X).astype(np.int64);R=np.zeros((C,NT),np.int32);K=np.zeros((C,NT),np.int32);B=np.zeros((C,NT),np.uint8);a=float(co[0]);w=np.asarray(co[1:],np.float32)
    for c in range(C):
      for t in range(NT):
        p=0 if t<ah.P else int(np.rint(a+float(np.dot(w,R[c,t-ah.P:t][::-1].astype(np.float32)))))
        e=int(Xi[c,t])-p;flo=e//STEP;cei=flo+1;vf=abs(e-STEP*flo)<=266;vc=abs(e-STEP*cei)<=266
        if not (vf or vc):raise RuntimeError(('no legal branch',c,t,e))
        usec=bool(vc and ((not vf) or gcost(cei)<gcost(flo)));k=cei if usec else flo;d=-RAD if usec else RAD;r=p+d+STEP*k
        if abs(int(Xi[c,t])-r)>RAD:raise RuntimeError(('hard-local',c,t,e,k,d,r))
        B[c,t]=1 if usec else 0;K[c,t]=k;R[c,t]=r
    return R,K,B
def replay(K,B,co):
    R=np.zeros(K.shape,np.int32);a=float(co[0]);w=np.asarray(co[1:],np.float32)
    for c in range(C):
      for t in range(NT):
        p=0 if t<ah.P else int(np.rint(a+float(np.dot(w,R[c,t-ah.P:t][::-1].astype(np.float32)))))
        d=-RAD if int(B[c,t]) else RAD;R[c,t]=p+d+STEP*int(K[c,t])
    return R
def main(path):
    with h5py.File(path,'r') as hf:
      d=hf['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,C0:C0+C],np.float64).T
    _,co=ah.fits(X);model,cod=cg.model_frame(co);R0,K0=ah.run_ar(X,cod);base_stream,base_entries,baserows=encode_k(K0)
    R,K,B=build_oracle(X,cod);me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('hard',me,eps))
    kstream,entries,krows=encode_k(K);Kd=cg.decode_components(entries,K.shape)
    if not np.array_equal(Kd,K):raise RuntimeError('K replay')
    packed=np.packbits(B.reshape(-1));zc=zstd.ZstdCompressor(level=19).compress(packed.tobytes());packed2=zstd.ZstdDecompressor().decompress(zc,max_output_size=len(packed))
    Bd=np.unpackbits(np.frombuffer(packed2,dtype=np.uint8))[:C*NT].reshape(C,NT).astype(np.uint8)
    if not np.array_equal(Bd,B):raise RuntimeError('choice replay')
    Rd=replay(Kd,Bd,cod)
    if not np.array_equal(Rd,R):raise RuntimeError('source replay')
    st=bit_context_stats(B,K);n=C*NT
    baseline_total=cg.OUTER_BYTES+len(model)+len(base_stream)
    k_only=cg.OUTER_BYTES+len(model)+len(kstream)
    choice_header=8
    exact_zstd_total=cg.OUTER_BYTES+len(model)+choice_header+len(zc)+len(kstream)
    raw_total=cg.OUTER_BYTES+len(model)+choice_header+len(packed)+len(kstream)
    out={'shape':[C,NT],'samples':n,'eps':eps,'maxerr':me,'incumbent_bytes':INC,'target_2x_bytes':TARGET,'baseline_reencoded_bytes':baseline_total,'oracle_k_only_bytes':k_only,'oracle_k_only_bps':8*k_only/n,'oracle_k_only_delta_vs_incumbent':k_only-INC,'choice_fraction_ceil':float(B.mean()),'choice_h0_bps':st['h0'],'choice_context_diagnostics':st,'choice_raw_packed_bytes':len(packed),'choice_zstd_bytes':len(zc),'exact_k_plus_raw_choice_bytes':raw_total,'exact_k_plus_zstd_choice_bytes':exact_zstd_total,'exact_zstd_delta_vs_incumbent':exact_zstd_total-INC,'component_rows':krows,'baseline_component_rows':baserows,'scope':'Recursive binary legal-phase headroom audit. At every sample a source-aware encoder chooses floor address with phase +133 or ceiling address with phase -133 using a gamma-like K cost; the resulting reconstruction changes all future AR32 predictions. K is physically encoded with frozen incumbent component coders. The binary phase field is explicitly materialized as packed bits and zstd, independently decoded, and together with K reproduces the exact recursive reconstruction under the unchanged hard error. K-only bytes deliberately omit the required choice stream and are an optimistic headroom diagnostic, not a codec. K+choice totals are fully replayable physical upper bounds.'}
    json.dump(out,open('imperial_gca_binary_phase_oracle.json','w'),indent=2);print(json.dumps({'summary':out},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
