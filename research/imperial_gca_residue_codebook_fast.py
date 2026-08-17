import json,struct,sys
import h5py,numpy as np
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as ah
import imperial_huber_ar32_component_zsm_gps as cg
import imperial_gca_residue_codebook as rc
C=128;NT=30000;C0=512;STEP=267;RAD=133;INC=2468803

def main(path):
  with h5py.File(path,'r') as hf:
    d=hf['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,C0:C0+C],np.float64).T
  _,co=ah.fits(X);model,cod=cg.model_frame(co);R0,K0=ah.run_ar(X,cod);P0=R0.astype(np.int64)-STEP*K0.astype(np.int64);N=np.rint(X).astype(np.int64)-P0
  cand=[]
  dg,_=rc.choose_phase(N,stride=32);cand.append(('global',{'d':dg}))
  pc,_=rc.choose_channel_phases(N);cand.append(('channel',{'pc':pc}))
  for B in (512,1024,2048,4096):
    pt,_=rc.choose_time_phases(N,B);cand.append(('time',{'B':B,'pt':pt}))
  rows=[{'mode':'zero','approx_proxy_bps':rc.k_proxy(K0),'side_bytes':0}];rank=[];print(json.dumps({'screen':rows[-1]}),flush=True)
  for mode,p in cand:
    D=rc.phase_matrix(mode,p);Ka=np.floor_divide(N-D.astype(np.int64)+RAD,STEP).astype(np.int32);side=len(rc.serialize_side(mode,p));pr=rc.k_proxy(Ka);adj=pr+8*side/(C*NT);r={'mode':mode,'B':int(p.get('B',0)),'approx_proxy_bps':pr,'charged_proxy_bps':adj,'side_bytes':side};rows.append(r);rank.append((adj,mode,p));print(json.dumps({'screen':r}),flush=True)
  rank.sort(key=lambda z:z[0]);best_exact=None
  for _,mode,p in rank[:3]:
    D=rc.phase_matrix(mode,p);R,K=rc.build_phase(X,cod,D);pr=rc.k_proxy(K);side=len(rc.serialize_side(mode,p));adj=pr+8*side/(C*NT);r={'mode':mode,'B':int(p.get('B',0)),'exact_recursive_proxy_bps':pr,'charged_recursive_proxy_bps':adj,'maxerr':float(np.max(np.abs(X-R.astype(np.float64))))};rows.append(r);print(json.dumps({'recursive':r}),flush=True)
    if best_exact is None or adj<best_exact[0]:best_exact=(adj,mode,p,R,K)
  if best_exact is None or best_exact[0]>=rc.k_proxy(K0):
    out={'winner':'incumbent','bytes':INC,'eps':eps,'screens':rows};json.dump(out,open('imperial_gca_residue_codebook_fast.json','w'),indent=2);print(json.dumps({'summary':out},indent=2),flush=True);return
  _,mode,p,R,K=best_exact;side=rc.serialize_side(mode,p);mode2,p2=rc.parse_side(side);D=rc.phase_matrix(mode2,p2);stream,entries,chosen=rc.encode_fixed(K);Kd=cg.decode_components(entries,K.shape)
  if not np.array_equal(Kd,K):raise RuntimeError('K replay')
  Rd=rc.decode_phase(Kd,cod,D)
  if not np.array_equal(Rd,R):raise RuntimeError('source replay')
  me=float(np.max(np.abs(X-Rd.astype(np.float64))));total=cg.OUTER_BYTES+len(model)+len(side)+len(stream)
  if me>eps*(1+5e-6):raise RuntimeError(('hard',me,eps))
  out={'winner':mode,'B':int(p.get('B',0)),'bytes':int(total),'bps':8*total/(C*NT),'delta_vs_incumbent':int(total-INC),'gain_vs_incumbent':INC/total,'side_bytes':len(side),'component_stream_bytes':len(stream),'maxerr':me,'eps':eps,'chosen':chosen,'screens':rows,'scope':'Fast exact gate for residue-class GCA. Compact phase rules are first ranked against the baseline AR32 predictor; only the top three are recursively materialized, and only the best charged recursive candidate is physically entropy-coded and independently decoded.'};json.dump(out,open('imperial_gca_residue_codebook_fast.json','w'),indent=2);print(json.dumps({'summary':out},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])