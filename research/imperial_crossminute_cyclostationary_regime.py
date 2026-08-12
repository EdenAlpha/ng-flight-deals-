import json,math,sys
import h5py,numpy as np

PERIODS=(1,2,4,5,10,20,25,50,100,125,250,500,1000)
WIDTHS=(128,64,32,16,8)
CB=128;BINS=512;OFF=256;ALPHA=.5

def stats(d):
 s=ss=0.;n=0
 for i in range(0,d.shape[0],2048):
  x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
 m=s/n;return m,float(np.sqrt(max(0.,ss/n-m*m)))
def qblock(d,c0,c1,eps):
 x=np.asarray(d[:,c0:c1],np.float64);q=np.rint(x/(2*eps)).astype(np.int16)
 if int(q.min())<-OFF or int(q.max())>=BINS-OFF:raise RuntimeError(('q range',int(q.min()),int(q.max())))
 return q
def score(q0,q1,qt,P):
 nt,w=qt.shape;phase=(np.arange(nt,dtype=np.int32)%P);shift=OFF
 def idx(q):return (phase[:,None]*BINS+(q.astype(np.int32)+shift)).ravel()
 tr=np.concatenate((idx(q0),idx(q1)));cnt=np.bincount(tr,minlength=P*BINS).astype(np.float64).reshape(P,BINS)
 nr=np.bincount(phase,minlength=P).astype(np.float64)*2*w;den=nr+ALPHA*BINS
 qi=qt.astype(np.int32)+shift;pr=(cnt[phase[:,None],qi]+ALPHA)/den[phase[:,None]]
 bits=float((-np.log2(pr)).sum())
 return bits,qt.size,float(np.mean(-np.log2(pr)))
def main(paths):
 fs=[h5py.File(p,'r') for p in paths]
 try:
  ds=[f['Acoustic'] for f in fs]
  if any(tuple(d.shape)!=(30000,6912) for d in ds):raise RuntimeError('shape drift')
  stds=[stats(d)[1] for d in ds];eps=[.1*s for s in stds]
  agg={(P,W):[0.,0] for P in PERIODS for W in WIDTHS};percb=[]
  for cb,c0 in enumerate(range(0,6912,CB)):
   c1=c0+CB;Q=[qblock(d,c0,c1,e) for d,e in zip(ds,eps)]
   for W in WIDTHS:
    if CB%W:continue
    for P in PERIODS:
     bits=0.;n=0
     for j in range(0,CB,W):
      b,nn,_=score(Q[0][:,j:j+W],Q[1][:,j:j+W],Q[2][:,j:j+W],P);bits+=b;n+=nn
     agg[(P,W)][0]+=bits;agg[(P,W)][1]+=n
     percb.append({'cb':cb,'c0':c0,'c1':c1,'period':P,'channel_context_width':W,'cross_entropy_bps':bits/n})
  combos=[]
  for (P,W),(bits,n) in agg.items():
   combos.append({'period':P,'channel_context_width':W,'cross_entropy_bps':bits/n,'ideal_bytes':bits/8,'samples':n,'gain_vs_verified_fullfile_sz3_bps':3.331839158950617/(bits/n),'gain_vs_tiled_sz3_bps':3.1097547839506174/(bits/n),'two_x_fullfile_sz3_target_bps':1.6659195794753086})
  combos.sort(key=lambda x:x['cross_entropy_bps'])
  # Compare each candidate to the same-width P=1 baseline; no target-trained model.
  base={r['channel_context_width']:r['cross_entropy_bps'] for r in combos if r['period']==1}
  for r in combos:r['improvement_vs_same_width_P1_bps']=base[r['channel_context_width']]-r['cross_entropy_bps']
  out={'shape':[30000,6912],'stds':stds,'eps':eps,'periods':list(PERIODS),'channel_context_widths':list(WIDTHS),'alpha':ALPHA,'combos':combos,'per_channel_block':percb,'scope':'Out-of-sample sequential cyclostationary/regime audit. Static symbol probabilities for target minute r2 are derived only from hard-error nearest lattice states of already-decoded previous minutes r0/r1, each normalized by its own 10%-std lattice. Context is decoder-known time phase t mod P and fixed channel subgroup. No target-trained counts and no model bytes are hidden. Report is ideal static arithmetic cross-entropy; not a compression claim until coder integration.'}
  print(json.dumps({'best':combos[:15]},indent=2),flush=True);json.dump(out,open('imperial_crossminute_cyclostationary_regime.json','w'),indent=2)
 finally:
  for f in fs:f.close()
if __name__=='__main__':main(sys.argv[1:])
