import json,numpy as np
meta=json.load(open('data/forge_subcube_meta.json'));eps=float(meta['eps_10pct_std'])
q=np.fromfile('hpez_final_quant_inds.bin',np.int32);coords=np.fromfile('hpez_final_quant_coords_u64.bin',np.uint64);eb=np.fromfile('hpez_final_quant_eb_f64.bin',np.float64)
if not(q.size==coords.size==eb.size):raise SystemExit(f'size mismatch q{q.size} c{coords.size} eb{eb.size}')
ends=[]
for line in open('hpez_level_ends.txt'):
 l,e=line.split();ends.append((int(l),int(e)))
rows=[];st=0
for level,e in ends:
 c=coords[st:e].astype(np.int64);v=eb[st:e];finite=np.isfinite(v);u=np.unique(np.round(v[finite]/eps,12),return_counts=True) if finite.any() else (np.array([]),np.array([]))
 base={'level':level,'n':int(e-st),'finite_n':int(finite.sum()),'eb_ratio_counts':[{ 'ratio_to_eps':float(a),'count':int(b)} for a,b in zip(*u)]}
 # Exact physical parity for this dyadic level.
 if finite.any() and level<=4:
  s=1<<(level-1);i=c//(64*512);rem=c%(64*512);j=rem//512;t=rem%512;pat=(((i//s)&1)<<2)|(((j//s)&1)<<1)|((t//s)&1)
  pars=[]
  for p in range(1,8):
   m=(pat==p)&finite
   if m.any():
    uu=np.unique(np.round(v[m]/eps,12),return_counts=True);pars.append({'pat':p,'n':int(m.sum()),'eb_ratio_counts':[{'ratio_to_eps':float(a),'count':int(b)} for a,b in zip(*uu)]})
  base['parity']=pars
 rows.append(base);st=e
out={'eps':eps,'rows':rows};print(json.dumps(out,indent=2));json.dump(out,open('hpez_error_allocation_analysis.json','w'),indent=2)
