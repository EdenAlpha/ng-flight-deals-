import json,sys
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as a

C=128;NT=30000;NCB=54;TB=1024;BLOCKS_PER_SLOT=6

def main(path,slot):
 slot=int(slot);lo=slot*BLOCKS_PER_SLOT;hi=min(NCB,lo+BLOCKS_PER_SLOT)
 a.NT=NT
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd
  if tuple(d.shape)!=(30000,6912):raise RuntimeError(('shape',d.shape))
  rows=[];raw_total=cand_total=huber_total=sz_total=0
  for cb in range(lo,hi):
   c0=cb*C;X=np.asarray(d[:,c0:c0+C],np.float64).T
   _,hu=a.fits(X);Rh,Kh=a.run_ar(X,hu)
   hme=float(np.max(np.abs(X-Rh.astype(np.float64))))
   if hme>eps*(1+1e-12):raise RuntimeError((cb,'huber hard',hme,eps))
   hub,hrep=a.backend_bytes(Kh)
   cab,nbit,nb,Kd=a.arithmetic(Kh)
   Rd=a.decode_source(Kd,hu);cme=float(np.max(np.abs(X-Rd.astype(np.float64))))
   if not np.array_equal(Kd,Kh):raise RuntimeError((cb,'K decode'))
   if not np.array_equal(Rd,Rh):raise RuntimeError((cb,'source decode'))
   if cme>eps*(1+1e-12):raise RuntimeError((cb,'candidate hard',cme,eps))
   sz=0
   tile_rows=[]
   for tb,t0 in enumerate(range(0,NT,TB)):
    t1=min(NT,t0+TB);sb,ori=a.m.szrun(X[:,t0:t1],eps);sz+=sb
    tile_rows.append({'tb':tb,'t0':t0,'ns':t1-t0,'sz3_bytes':sb,'sz3_orientation':ori})
   raw=X.size*2;raw_total+=raw;cand_total+=cab;huber_total+=hub;sz_total+=sz
   rr={'cb':cb,'c0':c0,'samples':int(X.size),'raw_bytes':raw,
       'huber_backend_bytes':hub,'huber_backend_bps':8*hub/X.size,'huber_backend_reps':hrep,
       'candidate_bytes':cab,'candidate_bps':8*cab/X.size,'gain_candidate_vs_huber_backend':hub/cab,
       'sz3_bytes':sz,'sz3_bps':8*sz/X.size,'gain_candidate_vs_sz3':sz/cab,
       'arithmetic_bits':nbit,'symbol_bits':nb,'maxerr':cme,'k_zero_fraction':float(np.mean(Kh==0)),'k_std':float(Kh.std()),
       'coefficients':hu.tolist(),'tiles':tile_rows}
   rows.append(rr);print(json.dumps({k:v for k,v in rr.items() if k not in ('coefficients','tiles')},indent=2),flush=True)
  out={'slot':slot,'channel_blocks':[lo,hi],'global_std':gstd,'eps':eps,'order':a.P,'step':a.STEP,
       'raw_bytes':raw_total,'candidate_bytes':cand_total,'huber_backend_bytes':huber_total,'sz3_bytes':sz_total,
       'ratio':raw_total/cand_total,'huber_backend_ratio':raw_total/huber_total,'sz3_ratio':raw_total/sz_total,
       'bps':16*cand_total/raw_total,'huber_backend_bps':16*huber_total/raw_total,'sz3_bps':16*sz_total/raw_total,
       'gain_vs_huber_backend':huber_total/cand_total,'gain_vs_sz3':sz_total/cand_total,
       'min_block_gain_vs_sz3':min(x['gain_candidate_vs_sz3'] for x in rows),
       'median_block_gain_vs_sz3':float(np.median([x['gain_candidate_vs_sz3'] for x in rows])),
       'rows':rows,
       'scope':'One ninth of the complete Imperial Acoustic array, promoting PR #402 without changing its algorithm. For every fixed 128-channel block, one shared float32 Huber267-IRLS AR32+intercept is fit only from t<1024 and then frozen for all 30,000 samples. The exact step267 K stream is coded from t=0 by the cold-start adaptive arithmetic backend with fixed unit priors and decoder-known previous-time/current-left clipped contexts; no K seed and no probability table are transmitted. AR model bytes, arithmetic framing and payload are charged. Exact K is decoded, the full recursive source trajectory is regenerated and hard-error checked. Matched SZ3 is rerun on the identical 128x1024 tiling and epsilon. Huber AR32 with the incumbent backend is also rerun as an internal control. No AI. Draft/do not merge.'}
  print(json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2),flush=True)
  json.dump(out,open(f'imperial_huber_ar32_coldstart_arithmetic_full_{slot}.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1],sys.argv[2])
