import json,sys,struct
import h5py,numpy as np
import imperial_defect_contour_address as c
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

TOP=(1<<32)-1
HALF=1<<31
Q1=1<<30
Q3=3<<30
FAMILIES=('global','prefix','prefix_c2','prefix_c4','prefix_t4','prefix_t8','prefix_ct2','prefix_neigh','prefix_c4t4')

class BitWriter:
    def __init__(self):
        self.buf=bytearray();self.cur=0;self.used=0;self.nbits=0
    def put(self,b):
        if b:self.cur|=1<<self.used
        self.used+=1;self.nbits+=1
        if self.used==8:
            self.buf.append(self.cur);self.cur=0;self.used=0
    def finish(self):
        if self.used:self.buf.append(self.cur)
        return bytes(self.buf),self.nbits

class ArithEncoder:
    def __init__(self):
        self.low=0;self.high=TOP;self.pending=0;self.w=BitWriter()
    def _emit(self,b):
        self.w.put(b);inv=1-b
        for _ in range(self.pending):self.w.put(inv)
        self.pending=0
    def encode(self,bit,zeros,ones):
        total=zeros+ones
        if total<=0:raise RuntimeError('bad arithmetic total')
        rng=self.high-self.low+1
        split=self.low+(rng*zeros)//total
        if bit==0:
            if zeros<=0:raise RuntimeError('impossible zero')
            self.high=split-1
        else:
            if ones<=0:raise RuntimeError('impossible one')
            self.low=split
        while True:
            if self.high<HALF:
                self._emit(0)
            elif self.low>=HALF:
                self._emit(1);self.low-=HALF;self.high-=HALF
            elif self.low>=Q1 and self.high<Q3:
                self.pending+=1;self.low-=Q1;self.high-=Q1
            else:break
            self.low=(self.low<<1)&TOP;self.high=((self.high<<1)&TOP)|1
    def finish(self):
        self.pending+=1
        self._emit(0 if self.low<Q1 else 1)
        return self.w.finish()

class BitReader:
    def __init__(self,data,nbits):self.data=data;self.nbits=int(nbits);self.pos=0
    def get(self):
        if self.pos>=self.nbits:
            self.pos+=1;return 0
        i=self.pos;self.pos+=1
        return (self.data[i>>3]>>(i&7))&1

class ArithDecoder:
    def __init__(self,data,nbits):
        self.low=0;self.high=TOP;self.r=BitReader(data,nbits);self.code=0
        for _ in range(32):self.code=((self.code<<1)|self.r.get())&TOP
    def decode(self,zeros,ones):
        total=zeros+ones;rng=self.high-self.low+1;split=self.low+(rng*zeros)//total
        if self.code<split:
            bit=0;self.high=split-1
        else:
            bit=1;self.low=split
        while True:
            if self.high<HALF:pass
            elif self.low>=HALF:
                self.low-=HALF;self.high-=HALF;self.code-=HALF
            elif self.low>=Q1 and self.high<Q3:
                self.low-=Q1;self.high-=Q1;self.code-=Q1
            else:break
            self.low=(self.low<<1)&TOP;self.high=((self.high<<1)&TOP)|1;self.code=((self.code<<1)&TOP)|self.r.get()
        return bit

def put_uvar(out,x):
    x=int(x)
    while x>=128:out.append((x&127)|128);x>>=7
    out.append(x)

def get_uvar(buf,pos):
    x=0;s=0
    while True:
        if pos>=len(buf):raise RuntimeError('uvar eof')
        b=buf[pos];pos+=1;x|=(b&127)<<s
        if b<128:return x,pos
        s+=7

def coords(shape):
    nc,nt=shape
    cc=np.repeat(np.arange(nc,dtype=np.uint64),nt)
    tt=np.tile(np.arange(nt,dtype=np.uint64),nc)
    return cc,tt

def context_keys(known,bit,family):
    flat=np.asarray(known,np.uint64).ravel();prefix=flat>>(bit+1);cc,tt=coords(known.shape);nc,nt=known.shape
    if family=='global':return np.zeros(flat.size,np.uint64)
    if family=='prefix':return prefix
    if family=='prefix_c2':return prefix*2+(cc*2//nc)
    if family=='prefix_c4':return prefix*4+(cc*4//nc)
    if family=='prefix_t4':return prefix*4+(tt*4//nt)
    if family=='prefix_t8':return prefix*8+(tt*8//nt)
    if family=='prefix_ct2':return prefix*4+(cc*2//nc)*2+(tt*2//nt)
    if family=='prefix_c4t4':return prefix*16+(cc*4//nc)*4+(tt*4//nt)
    if family=='prefix_neigh':
        H=((known>>(bit+1))&1).astype(np.uint64);L=np.zeros_like(H);U=np.zeros_like(H);L[1:,:]=H[:-1,:];U[:,1:]=H[:,:-1]
        return prefix*4+(L.ravel()<<1)+U.ravel()
    raise ValueError(family)

def groups_for(keys):
    order=np.argsort(keys,kind='stable');s=keys[order]
    if s.size==0:return order,np.zeros(0,np.int64),np.zeros(0,np.int64)
    cuts=np.flatnonzero(s[1:]!=s[:-1])+1;starts=np.r_[0,cuts].astype(np.int64);ends=np.r_[cuts,s.size].astype(np.int64)
    return order,starts,ends

def encode_candidate(B,known,bit,fid):
    family=FAMILIES[fid];keys=context_keys(known,bit,family);order,starts,ends=groups_for(keys);seq=np.asarray(B,np.uint8).ravel()[order]
    counts=bytearray();ks=[];ns=[]
    for a,z in zip(starts,ends):
        n=int(z-a);k=int(seq[a:z].sum());ns.append(n);ks.append(k);put_uvar(counts,k)
    craw=bytes(counts);cz=m.Z.compress(craw)
    if len(cz)<len(craw):cm=1;cstore=cz
    else:cm=0;cstore=craw
    ae=ArithEncoder()
    for a,z,k in zip(starts,ends,ks):
        rn=int(z-a);rk=int(k)
        for x in seq[a:z]:
            b=int(x)
            if rk!=0 and rk!=rn:ae.encode(b,rn-rk,rk)
            rn-=1;rk-=b
    araw,nbits=ae.finish();az=m.Z.compress(araw)
    if len(az)<len(araw):am=1;astore=az
    else:am=0;astore=araw
    head=struct.pack('<BBBIII',fid,cm,am,len(cstore),int(nbits),len(astore))
    payload=head+cstore+astore
    return payload,{'family':family,'groups':len(ks),'count_bytes':len(cstore),'arith_bytes':len(astore),'arith_bits':int(nbits),'ones':int(B.sum()),'stored':len(payload)}

def restricted_rank_frame(A):
    A=np.asarray(A,np.int32);u=m.zig(A);mx=int(u.max()) if u.size else 0;nb=max(1,mx.bit_length());known=np.zeros_like(u,np.uint64)
    out=bytearray(struct.pack('<4sHHB',b'RRA1',A.shape[0],A.shape[1],nb));detail=[]
    for bit in range(nb-1,-1,-1):
        B=((u>>bit)&1).astype(np.uint8);best=None
        for fid in range(len(FAMILIES)):
            payload,d=encode_candidate(B,known,bit,fid)
            if best is None or len(payload)<len(best[0]):best=(payload,d)
        payload,d=best;out.extend(payload);detail.append({'bit':bit,**d});known|=B.astype(np.uint64)<<bit
    buf=bytes(out)
    off=0;magic,nc,nt,nb2=struct.unpack_from('<4sHHB',buf,off);off+=9
    if magic!=b'RRA1' or (nc,nt)!=(A.shape[0],A.shape[1]) or nb2!=nb:raise RuntimeError('rank header')
    uu=np.zeros_like(u,np.uint64)
    for bit in range(nb-1,-1,-1):
        fid,cm,am,clen,nbits,alen=struct.unpack_from('<BBBIII',buf,off);off+=15;cstore=buf[off:off+clen];off+=clen;astore=buf[off:off+alen];off+=alen
        craw=m.D.decompress(cstore) if cm else cstore;araw=m.D.decompress(astore) if am else astore
        keys=context_keys(uu,bit,FAMILIES[fid]);order,starts,ends=groups_for(keys);ks=[];p=0
        for a,z in zip(starts,ends):
            k,p=get_uvar(craw,p);n=int(z-a)
            if k>n:raise RuntimeError(('count range',bit,k,n))
            ks.append(int(k))
        if p!=len(craw):raise RuntimeError(('count trailing',bit,p,len(craw)))
        ad=ArithDecoder(araw,nbits);sorted_bits=np.empty(A.size,np.uint8)
        for a,z,k in zip(starts,ends,ks):
            rn=int(z-a);rk=int(k)
            for j in range(int(a),int(z)):
                if rk==0:b=0
                elif rk==rn:b=1
                else:b=ad.decode(rn-rk,rk)
                sorted_bits[j]=b;rn-=1;rk-=b
            if rk!=0:raise RuntimeError(('rank remainder',bit,rk))
        Bflat=np.empty(A.size,np.uint8);Bflat[order]=sorted_bits;B=Bflat.reshape(A.shape);uu|=B.astype(np.uint64)<<bit
    if off!=len(buf):raise RuntimeError(('rank trailing',off,len(buf)))
    Ad=m.unzig(uu).astype(np.int32)
    if not np.array_equal(Ad,A):raise RuntimeError('restricted rank replay')
    return len(buf),'restricted_rank',Ad,detail

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);arb=g.ar32_baseline(X,eps);h,Q,E,dts,dcs,co,intercept,score,nz,changes=c.build_resonant(X,eps)
    rows=[]
    fr=m.encode_k(E);rows.append(c.validate(X,eps,h,Q,np.asarray(fr[2],np.int32),dts,dcs,co,intercept,int(fr[0]),'baseline_'+fr[1]))
    cb,cr,CE,cdetail=c.bitplane_contour_frame(E);rows.append(c.validate(X,eps,h,Q,CE,dts,dcs,co,intercept,cb,cr,cdetail))
    rb,rr,RE,rdetail=restricted_rank_frame(E);rows.append(c.validate(X,eps,h,Q,RE,dts,dcs,co,intercept,rb,rr,rdetail))
    for r in rows:
        r['gain_vs_sz3']=szb/r['bytes'];r['gain_vs_ar32']=arb['bytes']/r['bytes'];print(json.dumps({k:v for k,v in r.items() if k!='detail'},indent=2),flush=True)
    rows.sort(key=lambda x:x['bytes']);best=rows[0]
    out={'region':'hard','shape':[g.C,g.T],'samples':int(X.size),'global_std':std,'eps':eps,'h':h,'sz3':{'bytes':int(szb),'bps':8*szb/X.size,'orientation':ori},'ar32':arb,'rows':rows,'best':best,'rank_detail':rdetail,'scope':'Exact constrained-universe rank/address gate derived from the uploaded Complexity Weapon and NOVA ideas. The source reconstruction and charged learned sparse generator are identical to PR498/PR510. Only the exact defect witness representation changes. Zigzag defect planes are decoded from most-significant to least-significant. For each plane, already-decoded higher planes plus one small public coordinate grammar deterministically partition positions into context groups. The encoder sends each group exact one-count and arithmetic-ranks the observed group pattern under without-replacement probabilities, which is an actual finite-state implementation of locating the target among C(n,k) candidates rather than adding approximate restriction factors. Count blobs, per-plane grammar selectors, arithmetic payload, framing and optional Zstd wrapping are all in the real byte stream. Decoder parses the counts, reproduces the same context groups, arithmetic-decodes the exact plane, reconstructs the identical signed defect raster, regenerates the exact Q field from the charged learned generator, and must pass the unchanged hard source error. Context grammars include global, higher-bit prefix, channel/time partitions, joint partitions and decoder-known high-plane neighbor state. No ideal entropy or uncharged restriction is reported as achieved bytes.'}
    json.dump(out,open('imperial_defect_restricted_rank_address.json','w'),indent=2)
    print(json.dumps({'summary':{'best_rep':best['rep'],'bytes':best['bytes'],'rank_bytes':rb+best.get('model_bytes',0) if False else rb,'contour_total':next(r['bytes'] for r in rows if r['rep']=='bitplane_contour'),'ar32_bytes':arb['bytes'],'sz3_bytes':int(szb),'rank_total':next(r['bytes'] for r in rows if r['rep']=='restricted_rank')}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
