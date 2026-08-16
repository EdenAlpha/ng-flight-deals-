import json,sys
import h5py,numpy as np
import imperial_decoder_phase_automaton as m

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
C=128;NT=8192
TL=13;SL=7
BASE={
 'hard':{'ar32_bytes':661373,'sz3_bytes':754436},
 'easy':{'ar32_bytes':237943,'sz3_bytes':282633},
 'medium':{'ar32_bytes':416391,'sz3_bytes':460273},
 'far':{'ar32_bytes':551268,'sz3_bytes':636418},
}
HEADER=64

def legal(X,eps):
 lo=np.ceil(np.asarray(X,np.float64)-eps).astype(np.int32)
 hi=np.floor(np.asarray(X,np.float64)+eps).astype(np.int32)
 if np.any(lo>hi):raise RuntimeError('empty box')
 return lo,hi

def rdiv(num,den):
 num=int(num);den=int(den)
 return (num+den//2)//den if num>=0 else -((-num+den//2)//den)

def pred2(a,b,ia,ib,im):
 den=int(ib-ia);num=int(a)*(ib-im)+int(b)*(im-ia)
 return rdiv(num,den)

def mids(anchors):
 out=[]
 for a,b in zip(anchors[:-1],anchors[1:]):
  if b-a>1:out.append((a,b,(a+b)//2))
 return out

def refine_encoder(R,lo,hi,ca,ta,axis):
 if axis=='T':
  mm=mids(ta);E=np.empty((len(ca),len(mm)),np.int32)
  for i,c in enumerate(ca):
   for j,(a,b,z) in enumerate(mm):
    p=pred2(R[c,a],R[c,b],a,b,z);r=max(int(lo[c,z]),min(int(hi[c,z]),p));E[i,j]=r-p;R[c,z]=r
  ta=sorted(ta+[z for a,b,z in mm]);return ca,ta,E
 if axis=='S':
  mm=mids(ca);E=np.empty((len(mm),len(ta)),np.int32)
  for i,(a,b,z) in enumerate(mm):
   for j,t in enumerate(ta):
    p=pred2(R[a,t],R[b,t],a,b,z);r=max(int(lo[z,t]),min(int(hi[z,t]),p));E[i,j]=r-p;R[z,t]=r
  ca=sorted(ca+[z for a,b,z in mm]);return ca,ta,E
 raise ValueError(axis)

def refine_decoder(R,ca,ta,axis,E):
 if axis=='T':
  mm=mids(ta)
  if E.shape!=(len(ca),len(mm)):raise RuntimeError(('T shape',E.shape,len(ca),len(mm)))
  for i,c in enumerate(ca):
   for j,(a,b,z) in enumerate(mm):R[c,z]=pred2(R[c,a],R[c,b],a,b,z)+int(E[i,j])
  return ca,sorted(ta+[z for a,b,z in mm])
 if axis=='S':
  mm=mids(ca)
  if E.shape!=(len(mm),len(ta)):raise RuntimeError(('S shape',E.shape,len(mm),len(ta)))
  for i,(a,b,z) in enumerate(mm):
   for j,t in enumerate(ta):R[z,t]=pred2(R[a,t],R[b,t],a,b,z)+int(E[i,j])
  return sorted(ca+[z for a,b,z in mm]),ta
 raise ValueError(axis)

def interleave(nt,ns):
 out=[];ut=us=0
 while ut<nt or us<ns:
  if ut>=nt:out.append('S');us+=1;continue
  if us>=ns:out.append('T');ut+=1;continue
  ft=(ut+.5)/nt;fs=(us+.5)/ns
  if ft<=fs:out.append('T');ut+=1
  else:out.append('S');us+=1
 return ''.join(out)

def schedules():
 return {
  'time_first':'T'*TL+'S'*SL,
  'space_first':'S'*SL+'T'*TL,
  'balanced':interleave(TL,SL),
  'time_front':'T'*4+interleave(TL-4,SL),
  'space_front':'S'*3+interleave(TL,SL-3),
 }

def encode(X,eps,name,sched):
 lo,hi=legal(X,eps);R=np.zeros(X.shape,np.int32)
 corners=np.asarray([[int(np.rint(X[0,0])),int(np.rint(X[0,-1]))],[int(np.rint(X[-1,0])),int(np.rint(X[-1,-1]))]],np.int32)
 sf=m.encode_k(corners);sd=np.asarray(sf[2],np.int32)
 R[0,0]=sd[0,0];R[0,-1]=sd[0,1];R[-1,0]=sd[1,0];R[-1,-1]=sd[1,1]
 ca=[0,C-1];ta=[0,NT-1];frames=[];level=[];total=int(sf[0])+HEADER
 for k,axis in enumerate(sched):
  ca,ta,E=refine_encoder(R,lo,hi,ca,ta,axis)
  fr=m.encode_k(E);Kd=np.asarray(fr[2],np.int32);frames.append((axis,Kd));total+=int(fr[0])
  level.append({'level':k,'axis':axis,'shape':list(E.shape),'bytes':int(fr[0]),'bps_global':8*int(fr[0])/X.size,'zero_fraction':float(np.mean(E==0)),'abs1_fraction':float(np.mean(np.abs(E)==1)),'std':float(E.std()),'rep':fr[1]})
 if len(ca)!=C or len(ta)!=NT:raise RuntimeError(('incomplete encoder grid',len(ca),len(ta),name,sched))
 # Full independent decoder replay from only decoded seed + decoded level correction frames.
 Rd=np.zeros_like(R);Rd[0,0]=sd[0,0];Rd[0,-1]=sd[0,1];Rd[-1,0]=sd[1,0];Rd[-1,-1]=sd[1,1]
 ca=[0,C-1];ta=[0,NT-1]
 for axis,Kd in frames:ca,ta=refine_decoder(Rd,ca,ta,axis,Kd)
 if len(ca)!=C or len(ta)!=NT or not np.array_equal(Rd,R):raise RuntimeError(('decode replay',name))
 me=float(np.max(np.abs(X-Rd.astype(np.float64))))
 if me>eps*(1+1e-12):raise RuntimeError(('hard',name,me,eps))
 nonseed=X.size-4;nz=sum(int(np.count_nonzero(kd)) for _,kd in frames)
 return {'schedule_name':name,'schedule':sched,'bytes':int(total),'bps':8*total/X.size,'seed_bytes':int(sf[0]),'maxerr':me,'correction_nonzero_fraction':nz/nonseed,'levels':level,'time_level_bytes':sum(x['bytes'] for x in level if x['axis']=='T'),'space_level_bytes':sum(x['bytes'] for x in level if x['axis']=='S'),'median_level_zero_fraction':float(np.median([x['zero_fraction'] for x in level])),'fine4_zero_fraction':float(np.mean([x['zero_fraction'] for x in level[-4:]]))}

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
  if tuple(d.shape)!=(30000,6912):raise RuntimeError(('shape',d.shape))
  for region,c0 in SPECS:
   X=np.asarray(d[:NT,c0:c0+C],np.float64).T;rr=[]
   for name,sched in schedules().items():
    r=encode(X,eps,name,sched);r.update({'region':region,'c0':c0,'ar32_bytes':BASE[region]['ar32_bytes'],'sz3_bytes':BASE[region]['sz3_bytes'],'gain_vs_ar32':BASE[region]['ar32_bytes']/r['bytes'],'gain_vs_sz3':BASE[region]['sz3_bytes']/r['bytes']});rr.append(r)
    print(json.dumps({k:v for k,v in r.items() if k!='levels'},flush=True))
   best=min(rr,key=lambda x:x['bytes']);rows.append({'region':region,'best':best,'all':rr})
  out={'global_std':gstd,'eps':eps,'shape':[C,NT],'schedules':schedules(),'header_bytes':HEADER,'controls':'Pinned exact PR420 run 31788514939 on identical canonical 128x8192 regions and global epsilon. Every lifting correction frame is independently materialized and byte-decoded through the existing exact representation menu before full decoder replay.','rows':rows,'scope':'Hard-box multiresolution lifting codec. Four exact corner samples seed a decoder-known dyadic grid. A fixed schedule refines time and/or channel axes. Every newly introduced midpoint is linearly interpolated from its two already-decoded bracketing samples; if that prediction lies inside the source sample hard-error interval it emits correction zero, otherwise the encoder moves only to the nearest legal integer boundary and transmits that minimum correction. Each level correction field is a real raw/delta/Lorenzo/zigzag/XOR/Gray/bitplane Zstd frame, immediately byte-decoded. The final decoder starts from decoded corners and decoded level frames only, reproduces every sample, and verifies the unchanged source-domain max error. No post-hoc repair, target-trained model, ideal rate, or hidden state.'}
  json.dump(out,open('imperial_hardbox_multires_lifting.json','w'),indent=2)
  print(json.dumps({'summary':[{'region':x['region'],'schedule':x['best']['schedule_name'],'bytes':x['best']['bytes'],'bps':x['best']['bps'],'gain_ar32':x['best']['gain_vs_ar32'],'gain_sz3':x['best']['gain_vs_sz3'],'corr_nz':x['best']['correction_nonzero_fraction'],'median_level_zero':x['best']['median_level_zero_fraction'],'fine4_zero':x['best']['fine4_zero_fraction']} for x in rows]},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])