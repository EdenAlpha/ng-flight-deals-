import json,sys
import h5py,numpy as np,zstandard as zstd
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as h

C=128;NT=4096;TRAIN=1024;TB=1024
REGIONS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
WINS=(256,512,1024);MAXLAG=16
Z=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()

def h0(a):
 _,n=np.unique(np.asarray(a).ravel(),return_counts=True);p=n/n.sum();return float(-(p*np.log2(p)).sum())

def shifted(prev,t0,t1,lag):
 idx=np.arange(t0,t1,dtype=np.int32)+int(lag);out=np.zeros(t1-t0,np.int32);ok=(idx>=0)&(idx<NT);out[ok]=prev[idx[ok]];return out

def choose_map(K,win):
 nw=NT//win;lags=np.zeros((C,nw),np.int8);D=np.zeros_like(K,np.int32);D[0]=K[0]
 gains=[]
 for c in range(1,C):
  prev=K[c-1]
  for w,t0 in enumerate(range(0,NT,win)):
   t1=t0+win;x=K[c,t0:t1];best=(h0(x),99,None)
   # mode lag=99 means no cross-channel predictor. Otherwise exact shifted previous-channel K.
   for lag in range(-MAXLAG,MAXLAG+1):
    pr=shifted(prev,t0,t1,lag);d=x-pr;v=h0(d)
    if v<best[0]-1e-12:best=(v,lag,d)
   if best[1]==99:D[c,t0:t1]=x;lags[c,w]=99;gains.append(0.0)
   else:D[c,t0:t1]=best[2];lags[c,w]=best[1];gains.append(h0(x)-best[0])
 return D,lags,{'mean_local_h0_gain':float(np.mean(gains)) if gains else 0.0,'median_local_h0_gain':float(np.median(gains)) if gains else 0.0,'positive_windows':int(np.count_nonzero(np.asarray(gains)>1e-12)),'windows':len(gains)}

def decode_map(D,lags,win):
 K=np.zeros_like(D,np.int32);K[0]=D[0]
 for c in range(1,C):
  for w,t0 in enumerate(range(0,NT,win)):
   t1=t0+win;lag=int(lags[c,w]);pr=np.zeros(win,np.int32) if lag==99 else shifted(K[c-1],t0,t1,lag);K[c,t0:t1]=D[c,t0:t1]+pr
 return K

def evaluate(K,co,win,base,sz,X,eps):
 D,lags,diag=choose_map(K,win);ab,nbit,nb,Dd=h.arithmetic(D)
 raw=lags.tobytes();lb=Z.compress(raw);ld=np.frombuffer(ZD.decompress(lb),np.int8).reshape(lags.shape)
 if not np.array_equal(ld,lags):raise RuntimeError(('lag decode',win))
 Kd=decode_map(Dd,ld,win)
 if not np.array_equal(Dd,D) or not np.array_equal(Kd,K):raise RuntimeError(('K lag decode',win,int(np.count_nonzero(Kd!=K))))
 Rd=h.decode_source(Kd,co);me=float(np.max(np.abs(X-Rd.astype(np.float64))))
 if me>eps*(1+1e-12):raise RuntimeError(('hard',win,me,eps))
 total=int(ab)+len(lb)+24
 used=lags[1:].astype(np.int16);none=float(np.mean(used==99));active=used[used!=99]
 return {'window':win,'bytes':total,'bps':8*total/K.size,'arithmetic_bytes':int(ab),'lagmap_bytes':len(lb)+24,'arithmetic_bits':int(nbit),'symbol_bits':int(nb),'D_h0_bps':h0(D),'K_h0_bps':h0(K),'gain_vs_step267':base/total,'gain_vs_sz3':sz/total,'ratio_to_2x_target':total/(sz/2),'none_fraction':none,'mean_abs_lag':float(np.mean(np.abs(active))) if active.size else None,'lag_hist':{str(int(v)):int(n) for v,n in zip(*np.unique(active,return_counts=True))},'maxerr':me,**diag}

def main(path):
 h.C=C;h.NT=NT;h.TRAIN=TRAIN
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
  for region,c0 in REGIONS:
   X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,co=h.fits(X);R,K=h.run_ar(X,co);base,n0,nb0,D0=h.arithmetic(K);RR=h.decode_source(D0,co);me0=float(np.max(np.abs(X-RR.astype(np.float64))))
   if me0>eps*(1+1e-12):raise RuntimeError((region,'base hard',me0,eps))
   sz=0
   for t0 in range(0,NT,TB):q,_=m.szrun(X[:,t0:t0+TB],eps);sz+=int(q)
   vv=[]
   for win in WINS:
    r=evaluate(K,co,win,base,sz,X,eps);vv.append(r);print(json.dumps({'region':region,'variant':r},indent=2),flush=True)
   best=min(vv,key=lambda z:z['bytes']);row={'region':region,'c0':c0,'samples':int(K.size),'eps':eps,'step267_bytes':int(base),'step267_bps':8*base/K.size,'sz3_bytes':sz,'sz3_bps':8*sz/K.size,'best':best,'variants':vv};rows.append(row);print(json.dumps({'summary':row},indent=2),flush=True)
  out={'global_std':gstd,'eps':eps,'shape':[C,NT],'maxlag':MAXLAG,'windows':list(WINS),'rows':rows,'scope':'Exact decoder-real cross-channel lag-aligned innovation-symbol pilot. The incumbent Huber AR32 step267 K field and source reconstruction are unchanged. Channel 0 transmits K directly. For every later channel and each 256/512/1024-sample window, the encoder evaluates a no-predictor mode and integer lags -16..16 into the fully decoded previous channel K, selecting the mode that minimizes exact local zero-order entropy of D=K_current-shift(K_previous). The source-trained signed int8 lag map is Zstd-compressed, transmitted, decoded and charged. The transformed D field is exactly encoded/decoded with the incumbent cold-start contextual arithmetic backend. Decoder processes channels sequentially, reconstructs exact K from D plus the transmitted lag map, regenerates the incumbent source trajectory, and verifies the unchanged hard error. This is an executable screen for moveout/wavefront-style shifted cross-channel coherence, not an oracle with free lags. Matched incumbent step267 arithmetic and SZ3 controls are rerun on hard/easy/medium/far 128x4096 regions. No AI. Draft/do not merge.'};json.dump(out,open('imperial_ar32_lag_aligned_k_predictor.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
