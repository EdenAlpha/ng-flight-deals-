import json, math, sys
import h5py
import numpy as np
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as ah
import imperial_huber_ar32_component_zsm_gps as cg
import imperial_gca_residue_codebook as rc

C=128;NT=30000;C0=512;STEP=267;RAD=133
INC=2468803;MATCHED_SZ3=2767977;TARGET=MATCHED_SZ3/2.0

def local_cost(k):
    a=np.abs(np.asarray(k,dtype=np.int64));out=np.ones(a.shape,np.float64);nz=a>0
    if np.any(nz):
        q=np.floor(np.log2(a[nz])).astype(np.int64);out[nz]+=2.0+2.0*q
    return out

def choose_oracle(N,K0):
    # Across all legal phases d in [-133,133], K can only be one of
    # floor(N/267) or floor((N+266)/267). Choose the locally cheaper one.
    k0=np.floor_divide(N,STEP).astype(np.int32)
    k1=np.floor_divide(N+STEP-1,STEP).astype(np.int32)
    c0=local_cost(k0);c1=local_cost(k1)
    choose1=c1<c0
    ties=c1==c0
    # On exact local-code ties preserve the incumbent choice when possible;
    # this is deliberately conservative for context coding.
    choose1 |= ties & (k1==K0) & (k0!=K0)
    K=np.where(choose1,k1,k0).astype(np.int32)
    return K,k0,k1,c0,c1

def main(path):
    with h5py.File(path,'r') as hf:
        d=hf['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,C0:C0+C],np.float64).T
    Xi=np.rint(X).astype(np.int64)
    if int(math.floor(eps))!=RAD or np.max(np.abs(X-Xi))>1e-6:raise RuntimeError('source/eps')
    _,co=ah.fits(X);model,cod=cg.model_frame(co);R0,K0=ah.run_ar(X,cod)
    P0=R0.astype(np.int64)-STEP*K0.astype(np.int64);N=Xi-P0
    Ko,klo,khi,c0,c1=choose_oracle(N,K0)
    # Verify every selected K has at least one legal phase. Construct the
    # closest admissible phase to the exact remainder and check hard legality.
    raw=Xi-P0-STEP*Ko.astype(np.int64)
    D=np.clip(raw,-RAD,RAD).astype(np.int16)
    Ro=P0+D.astype(np.int64)+STEP*Ko.astype(np.int64)
    me=float(np.max(np.abs(X-Ro.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('oracle legality',me,eps))
    stream,entries,chosen=rc.encode_fixed(Ko)
    Kd=cg.decode_components(entries,Ko.shape)
    if not np.array_equal(Kd,Ko):raise RuntimeError('K decode')
    # Phase field is intentionally FREE in this oracle; bytes below omit D.
    total_no_phase=cg.OUTER_BYTES+len(model)+len(stream)
    base_proxy=rc.k_proxy(K0);oracle_proxy=rc.k_proxy(Ko)
    ambiguous=float(np.mean(klo!=khi));changed=float(np.mean(Ko!=K0));zero0=float(np.mean(K0==0));zeroo=float(np.mean(Ko==0))
    out={
      'scope':'Free per-sample phase oracle for the fixed audited Huber AR32 predictor. Every sample is allowed an individually chosen legal lattice phase at zero side-information cost, which is impossible as a real codec but gives the phase-only idea maximal freedom. The oracle then physically arithmetic-codes the resulting exact K field with the incumbent component configuration. Phase bytes are deliberately omitted and the result is therefore an optimistic diagnostic, not an achievable codec or rigorous universal lower bound.',
      'eps':eps,'maxerr':me,'samples':C*NT,'incumbent_bytes':INC,'matched_sz3_bytes':MATCHED_SZ3,'two_x_target_bytes':TARGET,
      'baseline_proxy_bps':base_proxy,'free_phase_proxy_bps':oracle_proxy,'proxy_gain_bps':base_proxy-oracle_proxy,
      'ambiguous_two_k_fraction':ambiguous,'changed_k_fraction':changed,'baseline_zero_fraction':zero0,'free_phase_zero_fraction':zeroo,
      'free_phase_k_stream_bytes':len(stream),'model_bytes':len(model),'outer_bytes':cg.OUTER_BYTES,'free_phase_total_excluding_phase_bytes':int(total_no_phase),
      'free_phase_bps_excluding_phase':8*total_no_phase/(C*NT),'gain_vs_incumbent_if_phase_free':INC/total_no_phase,
      'gain_vs_sz3_if_phase_free':MATCHED_SZ3/total_no_phase,'bytes_above_2x_target_if_phase_free':total_no_phase-TARGET,
      'chosen':chosen
    }
    json.dump(out,open('imperial_gca_free_phase_oracle.json','w'),indent=2);print(json.dumps({'summary':out},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
