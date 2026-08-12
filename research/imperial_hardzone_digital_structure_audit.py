import json,sys,math
import h5py,numpy as np,zstandard as zstd

T0=12000;NT=8192;NCH=32
REGIONS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
PHASES=np.arange(256,dtype=np.int32)
Z=zstd.ZstdCompressor(level=19)

def stats(d):
 s=ss=0.;n=0
 for i in range(0,d.shape[0],2048):
  x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
 m=s/n;return m,float(np.sqrt(max(0.,ss/n-m*m)))

def H(v):
 _,n=np.unique(np.asarray(v).ravel(),return_counts=True);p=n/n.sum();return float(-(p*np.log2(p)).sum())
def Hcond(a,b):
 a=np.asarray(a).ravel();b=np.asarray(b).ravel();pairs=np.stack([a,b],axis=1);_,n=np.unique(pairs,axis=0,return_counts=True);hp=H_from_counts(n);return hp-H(a)
def H_from_counts(n):
 n=np.asarray(n,float);p=n/n.sum();return float(-(p*np.log2(p)).sum())
def zig(q):
 q=np.asarray(q,np.int64);return ((q<<1)^(q>>63)).astype(np.uint64)
def qphase(x,phi):
 # exact nearest 256 grid with integer phase; ties use numpy round convention but max error remains <=128.
 return np.rint((np.asarray(x,np.float64)-float(phi))/256.0).astype(np.int16)
def rep_bytes(q):
 q=np.asarray(q,np.int16);zz=zig(q).astype(np.uint16);c=[]
 for name,a in [('raw',q),('dt',np.concatenate([q[:1],np.diff(q.astype(np.int32))]).astype(np.int32))]:
  mn=int(a.min());mx=int(a.max());dt=np.int8 if mn>=-128 and mx<=127 else np.int16
  c.append((len(Z.compress(a.astype(dt).tobytes())),name))
 # zigzag byte / bitplane style
 c.append((len(Z.compress(zz.tobytes())),'zigzag'))
 x=zz.copy();xd=x.copy();xd[1:]=x[1:]^x[:-1];c.append((len(Z.compress(xd.tobytes())),'zigzag_xort'))
 nb=max(1,int(zz.max()).bit_length());tot=0
 for k in range(nb):tot+=len(Z.compress(np.packbits(((zz>>k)&1).astype(np.uint8),bitorder='little').tobytes()))
 c.append((tot+4*nb,'zigzag_bitplanes'))
 return min(c)
def bitmetrics(u):
 u=np.asarray(u,np.uint16).ravel();rows=[]
 for k in range(16):
  b=((u>>k)&1).astype(np.uint8);ent=H(b);te=Hcond(b[:-1],b[1:]) if len(b)>1 else 0
  rows.append({'bit':k,'entropy':ent,'temporal_cond_entropy':te,'one_fraction':float(b.mean())})
 return rows

def trailing_zeros_abs(v):
 a=np.abs(np.asarray(v,np.int64)).ravel();a=a[a!=0]
 if not a.size:return 16.0
 z=[]
 for x in a:
  y=int(x);z.append((y & -y).bit_length()-1)
 return float(np.mean(z))
def mod_entropy(d,k):
 m=1<<k;return H(np.mod(np.asarray(d,np.int64),m).astype(np.int32))

def phase_screen_trace(x):
 x=np.asarray(x,np.int16);base=qphase(x,0);bb,br=rep_bytes(base);rows=[]
 # Actual compressed bytes for every byte phase. 8192*256 is cheap enough per trace.
 for p in range(256):
  q=qphase(x,p);b,r=rep_bytes(q);rows.append((b,p,r,H(q),H(np.diff(q.astype(np.int32)))))
 rows.sort()
 best=rows[0]
 return {'phase0_bytes':bb,'phase0_rep':br,'best_bytes':best[0],'best_phase':best[1],'best_rep':best[2],'gain_phase0_over_best':bb/best[0],
         'best_q_entropy':best[3],'best_delta_entropy':best[4],'top8':[{'bytes':r[0],'phase':r[1],'rep':r[2]} for r in rows[:8]]}

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,std=stats(d);eps=.1*std
  if eps<128:raise RuntimeError(('epsilon too small for 256 grid',eps))
  out={'std':std,'eps':eps,'window':[T0,T0+NT],'channels_per_region':NCH,'regions':[]}
  for name,c0 in REGIONS:
   X=np.asarray(d[T0:T0+NT,c0:c0+NCH],np.int16).T;u=X.view(np.uint16);lo=(u&255).astype(np.uint8);hi=(u>>8).astype(np.uint8)
   dt=np.diff(X.astype(np.int32),axis=1);ds=np.diff(X.astype(np.int32),axis=0)
   reg={'name':name,'c0':c0,'local_std':float(X.std()),'eps_over_local_std':eps/float(X.std()),'raw_value_entropy':H(X),'low_byte_entropy':H(lo),'high_byte_entropy':H(hi),
        'temporal_delta_entropy':H(dt),'spatial_delta_entropy':H(ds),'mean_temporal_diff_trailing_zeros':trailing_zeros_abs(dt),
        'clip_min_fraction':float(np.mean(X==-32768)),'clip_max_fraction':float(np.mean(X==32767)),
        'temporal_mod_entropy':{str(k):mod_entropy(dt,k) for k in range(4,17)},'raw_bitplanes':bitmetrics(u)}
   # 32 independent per-channel phase searches; metadata would be exactly 32 bytes here.
   ps=[phase_screen_trace(X[j]) for j in range(NCH)];reg['per_channel_phase']={'mean_gain':float(np.mean([r['gain_phase0_over_best'] for r in ps])),'median_gain':float(np.median([r['gain_phase0_over_best'] for r in ps])),'max_gain':max(r['gain_phase0_over_best'] for r in ps),'phase_histogram':{str(k):int(v) for k,v in zip(*np.unique([r['best_phase'] for r in ps],return_counts=True))},'rows':ps,
        'metadata_bits_per_sample_if_one_byte_per_channel':8/NT}
   # Common phase across entire region, selecting by sum of per-channel actual bytes.
   common=[]
   for p in range(256):
    s=0;reps={}
    for j in range(NCH):
     b,r=rep_bytes(qphase(X[j],p));s+=b;reps[r]=reps.get(r,0)+1
    common.append((s,p,reps))
   common.sort();p0=next(x for x in common if x[1]==0);best=common[0]
   reg['common_phase']={'phase0_bytes':p0[0],'best_bytes':best[0],'best_phase':best[1],'gain_phase0_over_best':p0[0]/best[0],'best_rep_counts':best[2]}
   out['regions'].append(reg);print(json.dumps({'name':name,'local_std':reg['local_std'],'lowH':reg['low_byte_entropy'],'highH':reg['high_byte_entropy'],'modH':reg['temporal_mod_entropy'],'phase':{k:v for k,v in reg['per_channel_phase'].items() if k!='rows'},'common':reg['common_phase']},indent=2),flush=True)
  out['scope']='Digital/instrument-coordinate audit on four deterministic 32-channel x 8192-sample Imperial windows. Reports raw byte/bitplane/modular structure and, crucially, searches every legal byte phase phi=0..255 for the fixed 256-spaced reconstruction grid. Because public epsilon exceeds 128, every phase has the same <=128 hard-error guarantee. Per-channel phase costs one byte/channel and is evaluated with actual Zstd representations (raw/delta/zigzag/XOR/bitplanes), not entropy alone. Diagnostic screen, no full-array codec claim.'
  json.dump(out,open('imperial_hardzone_digital_structure_audit.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
