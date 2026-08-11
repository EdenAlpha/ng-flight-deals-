import json,numpy as np,zstandard as zstd
meta=json.load(open('data/forge_subcube_meta.json'));eps=float(meta['eps_10pct_std'])
X=np.fromfile('data/forge_subcube_f32.bin','<f4').reshape(64,64,512).astype(np.float64)
R=np.fromfile('diagnostic_rec.bin','<f4').reshape(64,64,512).astype(np.float64)
q=np.fromfile('hpez_final_quant_inds.bin',np.int32);coords=np.fromfile('hpez_final_quant_coords_u64.bin',np.uint64);center=32768
phys=np.empty_like(q);phys[coords.astype(np.int64)]=q;Qh=phys.reshape(64,64,512)
Z=zstd.ZstdCompressor(level=19)

def H(a):
 _,c=np.unique(a,return_counts=True);p=c/c.sum();return float(-(p*np.log2(p)).sum())
def zstream(a):
 a=np.asarray(a);lo=int(a.min()) if a.size else 0;hi=int(a.max()) if a.size else 0;dt=np.int8 if lo>=-128 and hi<=127 else np.int16 if lo>=-32768 and hi<=32767 else np.int32
 raw=len(Z.compress(a.astype(dt).tobytes()));m=a!=0;mask=np.packbits(m,bitorder='little').tobytes();vals=a[m].astype(dt).tobytes();mv=len(Z.compress(mask+vals));return min(raw,mv),raw,mv

def design(pat, offsets, family):
 # target parity p2=(even i, odd j, even t), p4=(odd i, even j, even t).
 if pat==4:
  axis=0; targets=[(i,j,t) for i in range(3,61,2) for j in range(2,62,2) for t in range(max(12,max(abs(x) for x in offsets)),512-max(12,max(abs(x) for x in offsets)),2)]
 else:
  axis=1; targets=[(i,j,t) for i in range(2,62,2) for j in range(3,61,2) for t in range(max(12,max(abs(x) for x in offsets)),512-max(12,max(abs(x) for x in offsets)),2)]
 n=len(targets);F=[];names=[]
 # Construct columns vectorized from index arrays.
 I=np.array([x[0] for x in targets]);J=np.array([x[1] for x in targets]);T=np.array([x[2] for x in targets]);Y=X[I,J,T]
 def vals(ds,do,dt):
  return R[I+(ds if axis==0 else do), J+(do if axis==0 else ds), T+dt]
 for k in offsets:
  L=vals(-1,0,k);RR=vals(1,0,k)
  F.append((L+RR)*0.5);names.append(f'A1_{k}')
  if 'diff' in family:F.append((RR-L)*0.5);names.append(f'D1_{k}')
 if 'far' in family:
  for k in offsets:
   L=vals(-3,0,k);RR=vals(3,0,k);F.append((L+RR)*0.5);names.append(f'A3_{k}')
   if 'diff' in family:F.append((RR-L)*0.5);names.append(f'D3_{k}')
 if 'cross' in family:
  # Cross-axis coarse neighbours around each two primary parent traces, all on previous dyadic grid.
  for k in offsets[::max(1,len(offsets)//5)]:
   c=(vals(-1,-2,k)+vals(-1,2,k)+vals(1,-2,k)+vals(1,2,k))*0.25;F.append(c);names.append(f'C_{k}')
 F.append(np.ones(n));names.append('bias');A=np.stack(F,1)
 return A,Y,(I,J,T),names

def fit_eval(pat,offsets,family,lam):
 A,Y,idx,names=design(pat,offsets,family);I,J,T=idx
 # Ridge excluding bias; deterministic coefficients are side information.
 G=A.T@A;rhs=A.T@Y;scale=np.trace(G)/max(1,G.shape[0]);reg=lam*scale*np.eye(G.shape[0]);reg[-1,-1]=0
 try:w=np.linalg.solve(G+reg,rhs)
 except np.linalg.LinAlgError:w=np.linalg.lstsq(A,Y,rcond=1e-8)[0]
 P=A@w
 # Byte objective can benefit from tiny global lattice phase/bias shift. Search decoder-transmitted scalar bias around LS fit.
 best=None
 for frac in np.linspace(-1,1,33):
  Pb=P+frac*eps
  Q=np.rint((Y-Pb)/(2*eps)).astype(np.int16);rec=Pb+Q*(2*eps);me=float(np.max(np.abs(Y-rec)));zb,raw,mv=zstream(Q)
  r={'phase_frac_eps':float(frac),'zero_frac':float(np.mean(Q==0)),'H0':H(Q),'zstd':zb,'raw_zstd':raw,'maskval_zstd':mv,'maxerr':me}
  if best is None or r['zstd']<best['zstd']:best=r
 # Existing HPEZ q on exact same interior positions, mapped to signed compact lattice offsets; no sentinel expected here.
 h=Qh[I,J,T];hq=(h-center).astype(np.int16);hb,hr,hm=zstream(hq)
 # Coefficients: float32 + names/config/header. Charge conservatively.
 coeff_bytes=4*len(w)+32
 return {'pat':pat,'family':family,'offsets':list(offsets),'lambda':lam,'features':len(w),'coeff_bytes':coeff_bytes,'weights':w.tolist(),'best':best,'existing_same_region':{'center_frac':float(np.mean(h==center)),'H0':H(hq),'zstd':hb,'raw_zstd':hr,'maskval_zstd':hm},'interior_n':len(Y)}
rows=[]
configs=[]
for offs in [(-4,-2,0,2,4),(-8,-6,-4,-2,0,2,4,6,8),(-12,-10,-8,-6,-4,-2,0,2,4,6,8,10,12)]:
 for fam in ['avg','avg_diff','avg_far','avg_diff_far','avg_diff_far_cross']:
  for lam in [0,1e-8,1e-6,1e-4,1e-2]:configs.append((offs,fam,lam))
for pat in [2,4]:
 for offs,fam,lam in configs:
  r=fit_eval(pat,offs,fam,lam);rows.append(r);print('STENCIL',json.dumps({k:v for k,v in r.items() if k!='weights'}),flush=True)
rows.sort(key=lambda r:r['best']['zstd']+r['coeff_bytes'])
out={'eps':eps,'best':rows[:40]}
json.dump(out,open('hpez_spacetime_stencil_analysis.json','w'),indent=2);print('BEST',json.dumps([{k:v for k,v in r.items() if k!='weights'} for r in rows[:20]],indent=2),flush=True)
