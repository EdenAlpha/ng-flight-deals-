import json,sys,math
import h5py,numpy as np
import imperial_dyadic_shared_resonator as ar
import imperial_decoder_phase_automaton as m
import imperial_persistent_ar32_full_array_jit as aj

T0=14488;C0=512;C=32;T=4096;TRAIN=1024;P=32;STEP=267;OUTER_HEADER=32
MAGIC=b'HBR1'
PARTS=((32,4096),(32,2048),(32,1024),(32,512),(16,1024),(16,512),(8,1024),(8,512),(4,1024),(4,512),(2,1024),(1,4096))
aj.m.P=32;aj.m.m.STEP=STEP

# ---------- compact framing ----------
def uvar(v):
    v=int(v);o=bytearray()
    while True:
        b=v&127;v>>=7
        if v:o.append(b|128)
        else:o.append(b);break
    return bytes(o)
def read_uvar(buf,pos):
    v=0;s=0
    while True:
        if pos>=len(buf):raise RuntimeError('uvar eof')
        b=buf[pos];pos+=1;v|=(b&127)<<s
        if not b&128:return v,pos
        s+=7

class BitOut:
    def __init__(self):self.a=[]
    def put(self,b):self.a.append(1 if b else 0)
    def finish(self):
        if not self.a:return b''
        return np.packbits(np.asarray(self.a,np.uint8),bitorder='big').tobytes()
class BitIn:
    def __init__(self,b):self.b=b;self.p=0
    def get(self):
        if self.p>=len(self.b)*8:self.p+=1;return 0
        z=(self.b[self.p>>3]>>(7-(self.p&7)))&1;self.p+=1;return z

STATE=32;FULL=1<<STATE;HALF=FULL>>1;QUARTER=HALF>>1;THREE=3*QUARTER

def binom_rank_encode(bits):
    bits=np.asarray(bits,np.uint8).ravel();ones=int(bits.sum());zeros=len(bits)-ones
    if ones==0 or zeros==0:return b''
    rem0=zeros;rem1=ones;low=0;high=FULL-1;pending=0;bo=BitOut()
    def emit(bit,n):
        bo.put(bit)
        for _ in range(n):bo.put(1-bit)
    for bv in bits:
        total=rem0+rem1;rng=high-low+1
        if int(bv)==0:cl=0;ch=rem0
        else:cl=rem0;ch=total
        high=low+(rng*ch//total)-1;low=low+(rng*cl//total)
        while True:
            if high<HALF:emit(0,pending);pending=0
            elif low>=HALF:emit(1,pending);pending=0;low-=HALF;high-=HALF
            elif low>=QUARTER and high<THREE:pending+=1;low-=QUARTER;high-=QUARTER
            else:break
            low=(low<<1)&(FULL-1);high=((high<<1)|1)&(FULL-1)
        if int(bv)==0:rem0-=1
        else:rem1-=1
    pending+=1
    if low<QUARTER:emit(0,pending)
    else:emit(1,pending)
    return bo.finish()

def binom_rank_decode(blob,n,ones):
    ones=int(ones);zeros=n-ones
    if ones==0:return np.zeros(n,np.uint8)
    if zeros==0:return np.ones(n,np.uint8)
    rem0=zeros;rem1=ones;bi=BitIn(blob);low=0;high=FULL-1;code=0
    for _ in range(STATE):code=((code<<1)|bi.get())&(FULL-1)
    out=np.empty(n,np.uint8)
    for i in range(n):
        total=rem0+rem1;rng=high-low+1;value=((code-low+1)*total-1)//rng
        if value<rem0:b=0;cl=0;ch=rem0
        else:b=1;cl=rem0;ch=total
        high=low+(rng*ch//total)-1;low=low+(rng*cl//total)
        while True:
            if high<HALF:pass
            elif low>=HALF:low-=HALF;high-=HALF;code-=HALF
            elif low>=QUARTER and high<THREE:low-=QUARTER;high-=QUARTER;code-=QUARTER
            else:break
            low=(low<<1)&(FULL-1);high=((high<<1)|1)&(FULL-1);code=((code<<1)|bi.get())&(FULL-1)
        out[i]=b
        if b==0:rem0-=1
        else:rem1-=1
    if rem0 or rem1:raise RuntimeError(('binom remaining',rem0,rem1))
    return out

def enum_partition_encode(B,cb,tb):
    B=np.asarray(B,np.uint8);o=bytearray();ideal=0.0;rankbytes=0;tiles=0
    for c0 in range(0,B.shape[0],cb):
        c1=min(B.shape[0],c0+cb)
        for t0 in range(0,B.shape[1],tb):
            t1=min(B.shape[1],t0+tb);seq=B[c0:c1,t0:t1].ravel();n=len(seq);ones=int(seq.sum());z=n-ones
            pay=binom_rank_encode(seq);o+=uvar(ones)+uvar(len(pay))+pay;rankbytes+=len(pay);tiles+=1
            ideal+=(math.lgamma(n+1)-math.lgamma(ones+1)-math.lgamma(z+1))/math.log(2)
    return bytes(o),{'tiles':tiles,'rank_bytes':rankbytes,'ideal_bits':ideal}

def enum_partition_decode(raw,pos,shape,cb,tb):
    Cc,Tt=shape;B=np.empty((Cc,Tt),np.uint8)
    for c0 in range(0,Cc,cb):
        c1=min(Cc,c0+cb)
        for t0 in range(0,Tt,tb):
            t1=min(Tt,t0+tb);n=(c1-c0)*(t1-t0);ones,pos=read_uvar(raw,pos);bl,pos=read_uvar(raw,pos)
            if pos+bl>len(raw):raise RuntimeError('enum plane eof')
            seq=binom_rank_decode(raw[pos:pos+bl],n,ones);pos+=bl;B[c0:c1,t0:t1]=seq.reshape(c1-c0,t1-t0)
    return B,pos

def plane_candidates(B,part_ids):
    B=np.asarray(B,np.uint8);raw=np.packbits(B.ravel(),bitorder='little').tobytes();zb=m.Z.compress(raw)
    c=[{'mode':'zstd','mode_id':0,'body':uvar(len(zb))+zb,'payload_bytes':len(zb),'ideal_bits':None,'partition':None}]
    for pid,(cb,tb) in enumerate(PARTS,1):
        body,st=enum_partition_encode(B,cb,tb)
        c.append({'mode':'enum','mode_id':pid,'body':body,'payload_bytes':st['rank_bytes'],'ideal_bits':st['ideal_bits'],'partition':[cb,tb],'tiles':st['tiles']})
    for q in c:q['frame_bytes']=1+len(uvar(len(q['body'])))+len(q['body'])
    return sorted(c,key=lambda q:q['frame_bytes'])

def build_hybrid(K):
    u=m.zig(K);mx=int(u.max()) if u.size else 0;nb=max(1,mx.bit_length());s=bytearray(MAGIC);s+=uvar(K.shape[0])+uvar(K.shape[1])+uvar(nb);planes=[]
    for bit in range(nb):
        B=((u>>bit)&1).astype(np.uint8);cand=plane_candidates(B,PARTS);best=cand[0];body=best['body'];s.append(best['mode_id']);s+=uvar(len(body));s+=body
        planes.append({'bit':bit,'ones':int(B.sum()),'selected_mode':best['mode'],'selected_partition':best.get('partition'),'frame_bytes':best['frame_bytes'],'payload_bytes':best['payload_bytes'],'ideal_bits':best.get('ideal_bits'),'zstd_frame_bytes':next(x['frame_bytes'] for x in cand if x['mode']=='zstd'),'zstd_payload_bytes':next(x['payload_bytes'] for x in cand if x['mode']=='zstd'),'best_enum_frame_bytes':min(x['frame_bytes'] for x in cand if x['mode']=='enum'),'best_enum_partition':min((x for x in cand if x['mode']=='enum'),key=lambda x:x['frame_bytes'])['partition'],'candidate_frames':[{k:v for k,v in x.items() if k not in ('body',)} for x in cand]})
    raw=bytes(s);z=m.Z.compress(raw)
    if len(z)<len(raw):container=b'\x01'+z;outer='zstd'
    else:container=b'\x00'+raw;outer='raw'
    return container,{'nb':nb,'raw_bytes':len(raw),'container_bytes':len(container),'outer_rep':outer,'planes':planes}

def decode_hybrid(container):
    raw=m.D.decompress(container[1:]) if container[0]==1 else bytes(container[1:])
    if raw[:4]!=MAGIC:raise RuntimeError('hybrid magic')
    pos=4;Cc,pos=read_uvar(raw,pos);Tt,pos=read_uvar(raw,pos);nb,pos=read_uvar(raw,pos);u=np.zeros((Cc,Tt),np.uint64)
    for bit in range(nb):
        if pos>=len(raw):raise RuntimeError('plane tag eof')
        mode=raw[pos];pos+=1;flen,pos=read_uvar(raw,pos);end=pos+flen
        if end>len(raw):raise RuntimeError('plane frame eof')
        if mode==0:
            bl,pos2=read_uvar(raw,pos);z=raw[pos2:pos2+bl]
            if pos2+bl!=end:raise RuntimeError('zstd frame length')
            bb=m.D.decompress(z);bits=np.unpackbits(np.frombuffer(bb,np.uint8),bitorder='little')[:Cc*Tt].reshape(Cc,Tt).astype(np.uint8);pos=end
        else:
            if mode<1 or mode>len(PARTS):raise RuntimeError(('plane mode',mode))
            cb,tb=PARTS[mode-1];bits,p2=enum_partition_decode(raw,pos,(Cc,Tt),cb,tb)
            if p2!=end:raise RuntimeError(('enum frame length',mode,p2,end));pos=end
        u|=bits.astype(np.uint64)<<bit
    if pos!=len(raw):raise RuntimeError(('hybrid trailing',pos,len(raw)))
    return m.unzig(u).reshape(Cc,Tt)

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[T0:T0+T,C0:C0+C],np.float64).T
    co=ar.fit_shared(X[:,:TRAIN],P);mb,cd=ar.model_frame(co);R,K=aj.build(X,cd);fr=m.encode_k(K);Kd=np.asarray(fr[2],np.int32);Rd=aj.decode(Kd,cd)
    if not np.array_equal(Rd,R):raise RuntimeError('baseline replay')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('baseline hard',me,eps))
    baseline=int(mb)+int(fr[0])+OUTER_HEADER;szb,ori=m.szrun(X,eps)
    container,st=build_hybrid(K);KH=decode_hybrid(container)
    if not np.array_equal(KH,K):raise RuntimeError('hybrid K mismatch')
    RH=aj.decode(KH,cd)
    if not np.array_equal(RH,R):raise RuntimeError('hybrid AR replay')
    meh=float(np.max(np.abs(X-RH.astype(np.float64))))
    if meh>eps*(1+5e-6):raise RuntimeError(('hybrid hard',meh,eps))
    total=int(mb)+len(container)+OUTER_HEADER
    # Recompute incumbent bitplane payload for an apples-to-apples diagnostic.
    u=m.zig(K);nb=st['nb'];zplanes=[m.Z.compress(np.packbits(((u.ravel()>>b)&1).astype(np.uint8),bitorder='little').tobytes()) for b in range(nb)];inc_bp=sum(map(len,zplanes))+4*nb+40
    if fr[1]=='zigzag_bitplanes' and inc_bp!=int(fr[0]):raise RuntimeError(('incumbent bitplane accounting drift',inc_bp,fr[0]))
    out={'region':'hard','t0':T0,'c0':C0,'shape':[C,T],'samples':int(X.size),'global_std':std,'eps':eps,'ar_order':P,'step':STEP,'ar32':{'bytes':baseline,'bps':8*baseline/X.size,'innovation_bytes':int(fr[0]),'innovation_rep':fr[1],'model_bytes':int(mb),'maxerr':me},'sz3':{'bytes':int(szb),'bps':8*szb/X.size,'orientation':ori},'hybrid':{'bytes':total,'bps':8*total/X.size,'address_bytes':len(container),'address_raw_bytes':st['raw_bytes'],'outer_rep':st['outer_rep'],'gain_vs_ar32':baseline/total,'gain_vs_sz3':szb/total,'maxerr':meh,'nb':nb},'planes':st['planes'],'parts':[list(x) for x in PARTS],'scope':'Exact per-bitplane hybrid constrained-address codec for the incumbent AR32 step267 innovation stream. The AR32 reconstruction is frozen. Each zigzag innovation bitplane independently chooses the smaller actual frame between the incumbent packed-bitmap+Zstd representation and a finite binary combinatorial rank. Enumerative candidates partition the plane into public channel/time tiles; each tile transmits only its one-count and an arithmetic stream driven by exact remaining zero/one counts without replacement, making the rank finite and decoder-exact rather than an entropy estimate. Every plane selector, tile count and payload length is physically serialized. The whole hybrid address may receive one final outer Zstd pass. Decoder reconstructs every plane, exact K, exact AR32 state, and verifies the unchanged source hard-error bound. Incumbent encode_k and matched SZ3 are rerun on the identical hard 32x4096 object.'}
    json.dump(out,open('imperial_ar32_hybrid_bitplane_rank.json','w'),indent=2)
    print(json.dumps({'summary':{'hybrid_bytes':total,'ar32_bytes':baseline,'sz3_bytes':int(szb),'gain_ar32':baseline/total,'gain_sz3':szb/total,'address_bytes':len(container),'outer':st['outer_rep'],'planes':[{'bit':q['bit'],'mode':q['selected_mode'],'partition':q['selected_partition'],'frame':q['frame_bytes'],'zstd_frame':q['zstd_frame_bytes'],'best_enum_frame':q['best_enum_frame_bytes']} for q in st['planes']]}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
