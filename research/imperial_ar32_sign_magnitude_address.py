import json,sys,struct
import h5py,numpy as np
import imperial_ar32_autocomplexity_address as base
import imperial_defect_restricted_rank_address as rr
import imperial_defect_autocomplexity_rank as ac
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

FROZEN_HYBRID=23018
SIGN_FAMILIES=('global','prevsign','prev_left_sign','mag_prevsign','mag_prev_left_sign','mag_prev_left_diag_sign','mag_prevmag_prevsign')
MAGIC=b'SMG1'

def unsigned_auto_frame(M):
 M=np.asarray(M,np.uint64);mx=int(M.max()) if M.size else 0;nb=max(1,mx.bit_length());known=np.zeros_like(M,np.uint64);out=bytearray(struct.pack('<4sHHB',b'MAG1',M.shape[0],M.shape[1],nb));detail=[]
 for bit in range(nb-1,-1,-1):
  B=((M>>bit)&1).astype(np.uint8);best=None
  for fid in range(len(rr.FAMILIES)):
   payload,d=rr.encode_candidate(B,known,bit,fid);d={'mode':'static',**d}
   if best is None or len(payload)<len(best[0]):best=(payload,d)
  for cfid in range(len(ac.CAUSAL)):
   payload,d=ac.encode_causal_candidate(B,known,bit,cfid)
   if len(payload)<len(best[0]):best=(payload,d)
  payload,d=best;out.extend(payload);detail.append({'bit':bit,**d});known|=B.astype(np.uint64)<<bit
 buf=bytes(out);off=0;magic,nc,nt,nb2=struct.unpack_from('<4sHHB',buf,off);off+=9
 if magic!=b'MAG1' or (nc,nt)!=M.shape or nb2!=nb:raise RuntimeError('magnitude header')
 Md=np.zeros_like(M,np.uint64)
 for bit in range(nb-1,-1,-1):
  fid,cm,am,clen,nbits,alen=struct.unpack_from('<BBBIII',buf,off);off+=15;cstore=buf[off:off+clen];off+=clen;astore=buf[off:off+alen];off+=alen
  craw=m.D.decompress(cstore) if cm else cstore;araw=m.D.decompress(astore) if am else astore
  if fid<32:B=ac.decode_static_plane(fid,craw,araw,nbits,Md,bit,M.shape)
  else:B=ac.decode_causal_plane(fid,craw,araw,nbits,Md,bit,M.shape)
  Md|=B.astype(np.uint64)<<bit
 if off!=len(buf) or not np.array_equal(Md,M):raise RuntimeError('magnitude replay')
 return buf,Md,detail

def sign_state(K,c,t):
 if c<0 or t<0:return 0
 v=int(K[c,t]);return 0 if v==0 else (1 if v>0 else 2)
def sign_ctx(K,M,c,t,fam):
 ps=sign_state(K,c,t-1);ls=sign_state(K,c-1,t);ds=sign_state(K,c-1,t-1);mag=min(int(M[c,t]),7);pm=min(int(M[c,t-1]),7) if t>0 else 0
 if fam=='global':return (0,)
 if fam=='prevsign':return (ps,)
 if fam=='prev_left_sign':return (ps,ls)
 if fam=='mag_prevsign':return (mag,ps)
 if fam=='mag_prev_left_sign':return (mag,ps,ls)
 if fam=='mag_prev_left_diag_sign':return (mag,ps,ls,ds)
 if fam=='mag_prevmag_prevsign':return (mag,pm,ps)
 raise ValueError(fam)

def encode_sign(K,M,fid):
 fam=SIGN_FAMILIES[fid];counts={};e=rr.ArithEncoder();n=0
 for t in range(K.shape[1]):
  for c in range(K.shape[0]):
   if int(M[c,t])==0:continue
   q=sign_ctx(K,M,c,t,fam);a=counts.get(q)
   if a is None:a=[1,1];counts[q]=a
   b=1 if int(K[c,t])<0 else 0;e.encode(b,a[0],a[1]);a[b]+=1;n+=1
 raw,nbits=e.finish();z=m.Z.compress(raw)
 if len(z)<len(raw):zf=1;store=z
 else:zf=0;store=raw
 head=struct.pack('<4sBBII',b'SGN1',fid,zf,int(nbits),len(store));buf=head+store
 return buf,{'family':fam,'sign_symbols':n,'contexts':len(counts),'arith_bits':int(nbits),'payload_bytes':len(store),'frame_bytes':len(buf),'zstd':bool(zf)}
def decode_sign(buf,M):
 hs=struct.calcsize('<4sBBII');magic,fid,zf,nbits,nstore=struct.unpack_from('<4sBBII',buf,0)
 if magic!=b'SGN1' or hs+nstore!=len(buf):raise RuntimeError('sign header')
 raw=m.D.decompress(buf[hs:]) if zf else buf[hs:];d=rr.ArithDecoder(raw,nbits);K=np.zeros(M.shape,np.int32);fam=SIGN_FAMILIES[fid];counts={}
 for t in range(M.shape[1]):
  for c in range(M.shape[0]):
   mag=int(M[c,t])
   if mag==0:continue
   q=sign_ctx(K,M,c,t,fam);a=counts.get(q)
   if a is None:a=[1,1];counts[q]=a
   b=d.decode(a[0],a[1]);a[b]+=1;K[c,t]=-mag if b else mag
 return K

def full_frame(K):
 M=np.abs(np.asarray(K,np.int64)).astype(np.uint64);mbuf,Md,mdetail=unsigned_auto_frame(M);best=None
 for fid in range(len(SIGN_FAMILIES)):
  sbuf,sdetail=encode_sign(K,M,fid);Kd=decode_sign(sbuf,Md)
  if not np.array_equal(Kd,K):raise RuntimeError(('sign replay',SIGN_FAMILIES[fid]))
  total=12+len(mbuf)+len(sbuf)
  row=(total,sbuf,sdetail,Kd)
  if best is None or row[0]<best[0]:best=row
 total,sbuf,sdetail,Kd=best;buf=struct.pack('<4sII',MAGIC,len(mbuf),len(sbuf))+mbuf+sbuf
 magic,ml,sl=struct.unpack_from('<4sII',buf,0);off=12
 if magic!=MAGIC:raise RuntimeError('full signmag header')
 mm=buf[off:off+ml];off+=ml;ss=buf[off:off+sl];off+=sl
 # magnitude subframe independently decodes itself; reuse output already verified and parse via a helper call is unnecessary here because mm==mbuf was decoded above.
 if off!=len(buf):raise RuntimeError('full signmag trailing')
 K2=decode_sign(ss,Md)
 if not np.array_equal(K2,K):raise RuntimeError('full signmag K replay')
 return len(buf),'sign_magnitude_auto',K2,{'magnitude_bytes':len(mbuf),'sign_bytes':len(sbuf),'magnitude_planes':mdetail,'sign':sdetail,'header_bytes':12}

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
 szb,ori=m.szrun(X,eps);mb,cd,R,K=base.build_ar32(X);fb,rep,Kd,detail=full_frame(K)
 Rd=np.zeros_like(R)
 for c in range(K.shape[0]):
  for t in range(K.shape[1]):Rd[c,t]=g.ar.predict_hist(Rd,c,t,cd,g.P,'shared')+base.STEP*int(Kd[c,t])
 if not np.array_equal(Rd,R):raise RuntimeError('signmag AR replay')
 me=float(np.max(np.abs(X-Rd.astype(np.float64))))
 if me>eps*(1+5e-6):raise RuntimeError(('signmag hard',me,eps))
 total=int(mb)+fb+base.HEADER;out={'region':'hard','shape':[g.C,g.T],'samples':int(X.size),'global_std':std,'eps':eps,'step':base.STEP,'bytes':int(total),'bps':8*total/X.size,'model_bytes':int(mb),'address_bytes':fb,'maxerr':me,'rep':rep,'gain_vs_frozen_hybrid':FROZEN_HYBRID/total,'gain_vs_sz3':szb/total,'sz3_bytes':int(szb),'frozen_hybrid_bytes':FROZEN_HYBRID,'detail':detail,'scope':'Exact sign-magnitude coordinate test on the frozen AR32 step267 innovation field. The innovation magnitude |K| is encoded as unsigned bitplanes using the same exact AUTO-COMPLEXITY static/causal type-class competition, avoiding zigzag sign/magnitude interleaving. A separate time-major arithmetic sign stream is emitted only for nonzero magnitudes; its online decoder-known contexts may use current magnitude plus already decoded previous/left/diagonal sign states. No target-trained probability table is transmitted. The sign-family selector, magnitude frame, sign arithmetic payload and combined framing are real bytes. Decoder recovers identical K, identical AR32 R and verifies the unchanged hard source error.'};json.dump(out,open('imperial_ar32_sign_magnitude_address.json','w'),indent=2);print(json.dumps({k:v for k,v in out.items() if k!='detail'},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
