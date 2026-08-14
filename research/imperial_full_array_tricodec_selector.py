import json,sys,time,importlib.metadata
import h5py,numpy as np
from daspack import DASCoder,Quantizer
import imperial_huber_ar32_coldstart_arithmetic_regions as a

C=128;NT=30000;NCB=54;TB=1024;BLOCKS_PER_SLOT=6
DAS_BS=(128,2048);DAS_LEVELS=1;DAS_ORDER=1
# Conservative selector/container accounting: one mode byte + 4-byte payload length + 3 reserved bytes per 128-channel block.
SELECTOR_BYTES=8
# SZ3 is stored as independent <=1024-time streams, so charge a 4-byte length for every component stream.
SZ_TILE_LENGTH_BYTES=4

def main(path,slot):
 slot=int(slot);lo=slot*BLOCKS_PER_SLOT;hi=min(NCB,lo+BLOCKS_PER_SLOT);a.NT=NT
 version=importlib.metadata.version('daspack-dev');coder=DASCoder(threads=4)
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd;q=Quantizer.Uniform(step=2*eps)
  if tuple(d.shape)!=(30000,6912):raise RuntimeError(('shape',d.shape))
  rows=[];raw_total=ar_total=sz_total=das_total=sel_total=0;wins={'ar':0,'sz3':0,'daspack':0}
  for cb in range(lo,hi):
   c0=cb*C;X=np.asarray(d[:,c0:c0+C],np.float64).T
   # Candidate A: prefix-only Huber AR32 + exact cold-start contextual arithmetic.
   _,hu=a.fits(X);Rh,Kh=a.run_ar(X,hu);ar,nbit,nb,Kd=a.arithmetic(Kh);Rd=a.decode_source(Kd,hu)
   if not np.array_equal(Kd,Kh) or not np.array_equal(Rd,Rh):raise RuntimeError((cb,'AR decode'))
   ame=float(np.max(np.abs(X-Rd.astype(np.float64))))
   if ame>eps*(1+1e-12):raise RuntimeError((cb,'AR hard',ame,eps))
   # Candidate B: matched SZ3 on the incumbent 128x<=1024 tiling. Each component is independently decoded by szrun.
   sz_payload=0;sztiles=[]
   for t0 in range(0,NT,TB):
    t1=min(NT,t0+TB);n,ori=a.m.szrun(X[:,t0:t1],eps);sz_payload+=int(n)+SZ_TILE_LENGTH_BYTES;sztiles.append({'t0':t0,'bytes':int(n)+SZ_TILE_LENGTH_BYTES,'orientation':ori})
   # Candidate C: selected modern DASPack configuration from PR #400/#403, fully self-describing and decoded.
   XD=np.ascontiguousarray(X);t=time.perf_counter();stream=coder.encode(XD,q,blocksize=DAS_BS,levels=DAS_LEVELS,order=DAS_ORDER);et=time.perf_counter()-t
   t=time.perf_counter();DR=np.asarray(coder.decode(stream),np.float64);dt=time.perf_counter()-t
   if DR.shape!=XD.shape:raise RuntimeError((cb,'DASPack shape',DR.shape,XD.shape))
   dme=float(np.max(np.abs(XD-DR)))
   if dme>eps*(1+1e-10):raise RuntimeError((cb,'DASPack hard',dme,eps))
   das=len(stream)
   # All three candidates pay identical outer selector/framing bytes, so selection is actual-stream minimum.
   choices={'ar':int(ar)+SELECTOR_BYTES,'sz3':int(sz_payload)+SELECTOR_BYTES,'daspack':int(das)+SELECTOR_BYTES}
   winner=min(choices,key=choices.get);wb=choices[winner];wins[winner]+=1
   raw=int(X.size*2);raw_total+=raw;ar_total+=choices['ar'];sz_total+=choices['sz3'];das_total+=choices['daspack'];sel_total+=wb
   rr={'cb':cb,'c0':c0,'samples':int(X.size),'raw_bytes':raw,'winner':winner,'winner_bytes':wb,
       'ar_bytes':choices['ar'],'ar_bps':8*choices['ar']/X.size,'ar_maxerr':ame,'arithmetic_bits':int(nbit),'symbol_bits':int(nb),
       'sz3_bytes':choices['sz3'],'sz3_bps':8*choices['sz3']/X.size,'sz3_tiles':sztiles,
       'daspack_bytes':choices['daspack'],'daspack_bps':8*choices['daspack']/X.size,'daspack_maxerr':dme,'daspack_encode_seconds':et,'daspack_decode_seconds':dt,
       'gain_selector_vs_ar':choices['ar']/wb,'gain_selector_vs_sz3':choices['sz3']/wb,'gain_selector_vs_daspack':choices['daspack']/wb}
   rows.append(rr);print(json.dumps({k:v for k,v in rr.items() if k!='sz3_tiles'},indent=2),flush=True)
  out={'slot':slot,'channel_blocks':[lo,hi],'global_std':gstd,'eps':eps,'samples':sum(r['samples'] for r in rows),'raw_bytes':raw_total,
       'selector_bytes':sel_total,'ar_bytes':ar_total,'sz3_bytes':sz_total,'daspack_bytes':das_total,'winner_counts':wins,
       'selector_bps':16*sel_total/raw_total,'ar_bps':16*ar_total/raw_total,'sz3_bps':16*sz_total/raw_total,'daspack_bps':16*das_total/raw_total,
       'selector_ratio':raw_total/sel_total,'gain_selector_vs_ar':ar_total/sel_total,'gain_selector_vs_sz3':sz_total/sel_total,'gain_selector_vs_daspack':das_total/sel_total,
       'rows':rows,'daspack_version':version,'daspack_blocksize':list(DAS_BS),'daspack_levels':DAS_LEVELS,'daspack_order':DAS_ORDER,
       'scope':'Exact per-128-channel block selector over three independently executable hard-error codecs on the complete Imperial array. A = prefix-only Huber267 AR32 with exact cold-start contextual arithmetic; exact K and full source trajectory are decoded. B = matched SZ3 on 128x<=1024 tiles, each independently decoded by szrun, with an additional explicit 4-byte length charged per component stream. C = DASPack 0.0.1a0 channel-x-time blocksize128x2048 levels1/order1, complete self-describing stream decoded. Every candidate must satisfy the unchanged epsilon before selection. The shortest actual byte count wins for the block; all choices additionally pay the same conservative 8-byte outer mode/length framing. No target-trained selector model and no hidden oracle reconstruction. Nine slots cover all 54 blocks. No AI. Draft/do not merge.'}
  print(json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2),flush=True);json.dump(out,open(f'imperial_full_array_tricodec_selector_{slot}.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1],sys.argv[2])
