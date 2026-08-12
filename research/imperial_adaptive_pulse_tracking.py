import json,sys,math
import h5py,numpy as np,zstandard as zstd
from pysz import sz,szConfig,szErrorBoundMode

SAFETY=1-1e-5
REGIONS=(0,2304,4606,6880)
NCH=8
BASE_F=(0.5,1.0,2.0,4.0)
UP_F=(1.0,1.5,2.0)
DOWN_F=(0.5,0.75)
DEMODS=(False,True)
POLICIES=('nearest','hold')
Z=zstd.ZstdCompressor(level=19)

def stats(d):
 s=ss=0.;n=0
 for i in range(0,d.shape[0],2048):
  x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
 m=s/n;return m,float(np.sqrt(max(0.,ss/n-m*m)))

def szrun(X,eps):
 best=None
 for tr in (False,True):
  A=np.ascontiguousarray((X.T if tr else X).astype(np.float32));cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
  b,_=sz.compress(A,cfg);R,_=sz.decompress(b,np.float32,A.shape);me=float(np.max(np.abs(A-R)))
  if me>eps*(1+5e-6):raise RuntimeError(('sz hard error',me,eps))
  if best is None or int(b.size)<best[0]:best=(int(b.size),'T' if tr else 'C',me)
 return best

def pack2(sym):
 s=np.asarray(sym,np.uint8);n=s.size;pad=(-n)%4
 if pad:s=np.pad(s,(0,pad))
 s=s.reshape(-1,4)
 b=(s[:,0]|(s[:,1]<<2)|(s[:,2]<<4)|(s[:,3]<<6)).astype(np.uint8).tobytes()
 return Z.compress(b),n,pad

def encode_resets(q):
 q=np.asarray(q,np.int32);cands=[]
 if q.size==0:return 16,'none'
 for arr,name in ((q,'raw'),(np.diff(q,prepend=q[0]),'delta')):
  mn=int(arr.min());mx=int(arr.max())
  for dt in (np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4')):
   if mn>=np.iinfo(dt).min and mx<=np.iinfo(dt).max:
    cands.append((len(Z.compress(arr.astype(dt).tobytes()))+20,name+'_'+dt.str));break
 return min(cands)

def pulse_encode(x,eps,basef,upf,downf,demod,policy):
 x=np.asarray(x,np.float64);n=x.size
 sign=np.where((np.arange(n)&1)==0,1.0,-1.0) if demod else np.ones(n)
 z=x*sign
 base=max(0.125*eps,basef*eps);s=base;smin=.125*eps;smax=32*eps
 reset_step=2*eps*SAFETY
 y=0.;prev=0
 sym=np.empty(n,np.uint8);resets=[];R=np.empty(n,np.float64)
 pulse_counts=[0,0,0,0]
 for t in range(n):
  target=z[t];cands=[]
  for u,code in ((-1,0),(0,1),(1,2)):
   yy=y+u*s
   if abs(target-yy)<=eps*(1-2e-6):
    if policy=='nearest':key=(abs(target-yy),0 if u==0 else 1,0 if u==prev else 1)
    else:key=(0 if u==0 else 1,0 if u==prev else 1,abs(target-yy))
    cands.append((key,u,code,yy))
  if cands:
   _,u,code,yy=min(cands,key=lambda a:a[0]);sym[t]=code;y=yy
   if u!=0 and u==prev:s=min(smax,s*upf)
   elif u==0:s=max(smin,s*downf)
   else:s=max(smin,s*downf)
   prev=u
  else:
   q=int(np.rint(target/reset_step));y=q*reset_step
   if abs(target-y)>eps*(1+1e-8):raise RuntimeError(('reset hard error',target,y,eps))
   sym[t]=3;resets.append(q);s=base;prev=0
  R[t]=y*sign[t];pulse_counts[int(sym[t])]+=1
 me=float(np.max(np.abs(x-R)))
 if me>eps*(1+5e-6):raise RuntimeError(('pulse hard error',me,eps))
 pb,nn,pad=pack2(sym);rb,rrep=encode_resets(resets)
 total=len(pb)+rb+32
 p=np.asarray(pulse_counts,np.float64)/n;p=p[p>0];H=float(-(p*np.log2(p)).sum())
 return {'bytes':total,'pulse_bytes':len(pb),'reset_bytes':rb,'reset_rep':rrep,'resets':len(resets),'reset_fraction':len(resets)/n,'pulse_hist':pulse_counts,'pulse_entropy_bps':H,'bps':8*total/n,'maxerr':me,'packed_padding':pad}

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,std=stats(d);eps=.1*std
  rows=[];region_summary=[]
  for c0 in REGIONS:
   c1=min(c0+NCH,d.shape[1]);X=np.asarray(d[:,c0:c1],np.float64)
   sb=szrun(X,eps);regbytes=0;resets=0;hist=np.zeros(4,np.int64);chosen=[]
   for j in range(X.shape[1]):
    best=None
    for bf in BASE_F:
     for uf in UP_F:
      for df in DOWN_F:
       for dm in DEMODS:
        for pol in POLICIES:
         r=pulse_encode(X[:,j],eps,bf,uf,df,dm,pol)
         row=(r['bytes'],bf,uf,df,dm,pol,r)
         if best is None or row[0]<best[0]:best=row
    b,bf,uf,df,dm,pol,r=best
    b+=1 # explicit per-channel selector byte; candidate menu is fixed decoder-known
    regbytes+=b;resets+=r['resets'];hist+=np.asarray(r['pulse_hist'],np.int64)
    rr=dict(r);rr.update({'region_c0':c0,'channel':c0+j,'base_over_eps':bf,'up':uf,'down':df,'nyquist_demod':dm,'policy':pol,'bytes_with_selector':b,'gain_vs_region_sz3_if_same_bps':(8*sb[0]/X.size)/(8*b/X.shape[0])})
    rows.append(rr);chosen.append(rr)
   n=X.size;p=hist.astype(np.float64)/hist.sum();p=p[p>0];H=float(-(p*np.log2(p)).sum())
   region_summary.append({'c0':c0,'channels':X.shape[1],'samples':n,'pulse_bytes':regbytes,'pulse_bps':8*regbytes/n,'sz3_bytes':sb[0],'sz3_bps':8*sb[0]/n,'gain_vs_sz3':sb[0]/regbytes,'reset_fraction':resets/n,'aggregate_symbol_entropy_bps':H,'pulse_hist':hist.tolist(),'sz3_orientation':sb[1],'sz3_maxerr':sb[2]})
  totaln=sum(r['samples'] for r in region_summary);pb=sum(r['pulse_bytes'] for r in region_summary);szb=sum(r['sz3_bytes'] for r in region_summary);resh=sum(r['pulse_hist'][3] for r in region_summary)
  out={'shape_full':list(d.shape),'std':std,'eps':eps,'regions':list(REGIONS),'channels_per_region':NCH,'candidate_menu':{'base_over_eps':list(BASE_F),'up':list(UP_F),'down':list(DOWN_F),'nyquist_demod':list(DEMODS),'policy':list(POLICIES)},'aggregate':{'samples':totaln,'pulse_bytes':pb,'sz3_bytes':szb,'pulse_bps':8*pb/totaln,'sz3_bps':8*szb/totaln,'gain_vs_sz3':szb/pb,'reset_fraction':resh/totaln,'strict_2x_target_bps_from_fullfile_sz3':3.331839158950617/2},'regions_summary':region_summary,'rows':rows,'scope':'Adaptive pulse-state DAS screen. Decoder state is driven only by a 4-symbol stream {down,hold,up,reset}; step size evolves deterministically from the pulse history. Resets transmit a legal coarse reconstruction state. All pulse symbols are actually 2-bit packed and Zstd-compressed; reset values are serialized; one explicit selector byte per channel pays for target-adaptive parameter choice. Final samples are independently checked against the unchanged 10%-global-std hard maximum error. Matched SZ3 is rerun on each identical full-minute 8-channel region. Screen only, not a whole-array claim.'}
  print(json.dumps({'aggregate':out['aggregate'],'regions':region_summary},indent=2),flush=True);json.dump(out,open('imperial_adaptive_pulse_tracking.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
