import json,sys,os
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import h5py,numpy as np
from research.imperial_dualview_modulo_correction import stats,szrun,run,C,T,SAFETY
CASES=[(2,'temporal'),(2,'median'),(4,'temporal'),(4,'median'),(8,'temporal'),(8,'median')]
def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,std=stats(d);eps=.1*std;b=eps*SAFETY;specs=[('early',0,3392),('center',14488,3392),('edge',14488,6784)];rows=[];sz={}
  for name,t0,c0 in specs:
   X=np.asarray(d[t0:t0+T,c0:c0+C],np.float64).T;sb=szrun(X,eps);sz[name]=sb
   for M,side in CASES:
    r=run(X,b,2,False,0.25,M,side);r.update(tile=name,sz3_bytes=sb,gain_vs_sz3=sb/r['bytes'],bps=8*r['bytes']/X.size);rows.append(r)
  combos=[];ss=sum(sz.values())
  for M,side in CASES:
   rr=[r for r in rows if r['M']==M and r['side']==side];bb=sum(r['bytes'] for r in rr);combos.append({'M':M,'side':side,'bytes':bb,'sz3_bytes':ss,'gain_vs_sz3':ss/bb,'bps':8*bb/(C*T*len(rr)),'min_tile_gain':min(r['gain_vs_sz3'] for r in rr),'control_bytes':sum(r['control_bytes'] for r in rr),'residue_bytes':sum(r['residue_bytes'] for r in rr),'escape_bytes':sum(r['escape_bytes'] for r in rr),'median_escape_fraction':float(np.median([r['escape_fraction'] for r in rr])),'median_residue_entropy':float(np.median([r['residue_entropy'] for r in rr]))})
  combos.sort(key=lambda x:x['bytes']);out={'std':std,'eps':eps,'fixed_parent_phase':2,'fixed_parent_weight':0.25,'tiles':[x[0] for x in specs],'combos':combos,'rows':rows,'scope':'Fast precommitted directional gate for PR247. Same modulo-correction implementation, only parent-neighborhood phase2/no-demod/weight0.25 and M2/4/8 with temporal or median side view on early/center/edge tiles.'};print(json.dumps(out,indent=2),flush=True);json.dump(out,open('imperial_dualview_modulo_fastgate.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
