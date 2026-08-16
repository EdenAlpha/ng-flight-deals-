import json,sys,struct
import h5py,numpy as np
import imperial_ar32_autocomplexity_address as base
import imperial_defect_autocomplexity_rank as ac
import imperial_defect_restricted_rank_address as br
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

FAMILIES=('global','prev4','prev8','c4_prev4','c8_prev4','chan_prev4','prev4_left4','prev4_left4_diag4','c4_prev4_left4','c8_prev4_left4')
MAGIC=b'STC1';FRAME_HEAD=struct.calcsize('<4sBBBBIII')

def clipv(x,r):return max(-r,min(r,int(x)))+r

def ctx(A,c,t,fam):
    C=A.shape[0];p=int(A[c,t-1]) if t>0 else 0;l=int(A[c-1,t]) if c>0 else 0;d=int(A[c-1,t-1]) if c>0 and t>0 else 0
    p4=clipv(p,4);l4=clipv(l,4);d4=clipv(d,4)
    if fam=='global':return 0
    if fam=='prev4':return p4
    if fam=='prev8':return clipv(p,8)
    if fam=='c4_prev4':return (c*4//C)*9+p4
    if fam=='c8_prev4':return (c*8//C)*9+p4
    if fam=='chan_prev4':return c*9+p4
    if fam=='prev4_left4':return p4*9+l4
    if fam=='prev4_left4_diag4':return (p4*9+l4)*9+d4
    if fam=='c4_prev4_left4':return (c*4//C)*81+p4*9+l4
    if fam=='c8_prev4_left4':return (c*8//C)*81+p4*9+l4
    raise ValueError(fam)

def zz(v):return 2*int(v) if v>=0 else -2*int(v)-1
def unzz(u):return int(u//2) if (u&1)==0 else -int((u+1)//2)

class Fenwick:
    def __init__(self,a):
        self.n=len(a);self.a=[int(x) for x in a];self.t=[0]*(self.n+1)
        for i,x in enumerate(self.a):
            j=i+1
            while j<=self.n:self.t[j]+=x;j+=j&-j
    def total(self):return self.sum(self.n)
    def sum(self,i):
        s=0
        while i:s+=self.t[i];i-=i&-i
        return s
    def update(self,i,delta):
        self.a[i]+=delta;j=i+1
        while j<=self.n:self.t[j]+=delta;j+=j&-j
    def find(self,v):
        # smallest index i with prefix(i+1)>v
        idx=0;bit=1<<(self.n.bit_length()-1);s=0
        while bit:
            j=idx+bit
            if j<=self.n and s+self.t[j]<=v:idx=j;s+=self.t[j]
            bit>>=1
        if idx>=self.n:raise RuntimeError(('fenwick find',v,self.total()))
        return idx

class MultiEncoder:
    def __init__(self):self.low=0;self.high=br.TOP;self.pending=0;self.w=br.BitWriter()
    def emit(self,b):
        self.w.put(b);q=1-b
        for _ in range(self.pending):self.w.put(q)
        self.pending=0
    def encode(self,cum,freq,total):
        rng=self.high-self.low+1;old=self.low
        self.low=old+(rng*cum)//total;self.high=old+(rng*(cum+freq))//total-1
        while True:
            if self.high<br.HALF:self.emit(0)
            elif self.low>=br.HALF:self.emit(1);self.low-=br.HALF;self.high-=br.HALF
            elif self.low>=br.Q1 and self.high<br.Q3:self.pending+=1;self.low-=br.Q1;self.high-=br.Q1
            else:break
            self.low=(self.low<<1)&br.TOP;self.high=((self.high<<1)&br.TOP)|1
    def finish(self):self.pending+=1;self.emit(0 if self.low<br.Q1 else 1);return self.w.finish()

class MultiDecoder:
    def __init__(self,data,nbits):
        self.low=0;self.high=br.TOP;self.r=br.BitReader(data,nbits);self.code=0
        for _ in range(32):self.code=((self.code<<1)|self.r.get())&br.TOP
    def target(self,total):
        rng=self.high-self.low+1
        return ((self.code-self.low+1)*total-1)//rng
    def consume(self,cum,freq,total):
        rng=self.high-self.low+1;old=self.low
        self.low=old+(rng*cum)//total;self.high=old+(rng*(cum+freq))//total-1
        while True:
            if self.high<br.HALF:pass
            elif self.low>=br.HALF:self.low-=br.HALF;self.high-=br.HALF;self.code-=br.HALF
            elif self.low>=br.Q1 and self.high<br.Q3:self.low-=br.Q1;self.high-=br.Q1;self.code-=br.Q1
            else:break
            self.low=(self.low<<1)&br.TOP;self.high=((self.high<<1)&br.TOP)|1;self.code=((self.code<<1)&br.TOP)|self.r.get()

def build_hist(K,fam):
    h={}
    for t in range(K.shape[1]):
        for c in range(K.shape[0]):
            q=ctx(K,c,t,fam);v=int(K[c,t]);d=h.setdefault(q,{});d[v]=d.get(v,0)+1
    return h

def meta_encode(hist):
    raw=bytearray();br.put_uvar(raw,len(hist));last=-1
    for q in sorted(hist):
        br.put_uvar(raw,q-last-1);last=q;items=sorted(hist[q].items(),key=lambda z:zz(z[0]));br.put_uvar(raw,len(items));prev=-1
        for v,n in items:
            u=zz(v);br.put_uvar(raw,u-prev-1);prev=u;br.put_uvar(raw,n)
    raw=bytes(raw);z=m.Z.compress(raw)
    return (z,1) if len(z)<len(raw) else (raw,0)

def meta_decode(blob,zflag):
    raw=m.D.decompress(blob) if zflag else blob;p=0;nctx,p=br.get_uvar(raw,p);h={};q=-1
    for _ in range(nctx):
        dq,p=br.get_uvar(raw,p);q+=dq+1;ne,p=br.get_uvar(raw,p);d={};u=-1
        for _ in range(ne):
            du,p=br.get_uvar(raw,p);u+=du+1;n,p=br.get_uvar(raw,p);d[unzz(u)]=int(n)
        h[q]=d
    if p!=len(raw):raise RuntimeError(('meta trailing',p,len(raw)))
    return h

def state_from_hist(hist):
    st={}
    for q,d in hist.items():
        syms=sorted(d,key=zz);counts=[d[v] for v in syms];st[q]=(syms,{v:i for i,v in enumerate(syms)},Fenwick(counts))
    return st

def encode_family(K,fid):
    fam=FAMILIES[fid];hist=build_hist(K,fam);meta,zf=meta_encode(hist);state=state_from_hist(hist);enc=MultiEncoder()
    for t in range(K.shape[1]):
        for c in range(K.shape[0]):
            q=ctx(K,c,t,fam);v=int(K[c,t]);syms,idx,fw=state[q];i=idx[v];total=fw.total();freq=fw.a[i]
            if freq<=0:raise RuntimeError(('empty encode',fam,q,v))
            if len(syms)>1 and freq<total:enc.encode(fw.sum(i),freq,total)
            fw.update(i,-1)
    bits,nbits=enc.finish();zb=m.Z.compress(bits)
    if len(zb)<len(bits):af=1;store=zb
    else:af=0;store=bits
    head=struct.pack('<4sBBBBIII',MAGIC,fid,zf,af,0,len(meta),int(nbits),len(store));buf=head+meta+store
    return buf,{'family':fam,'contexts':len(hist),'meta_bytes':len(meta),'arith_bytes':len(store),'arith_bits':int(nbits),'frame_bytes':len(buf)}

def decode_frame(buf,shape):
    off=0;magic,fid,zf,af,_,mlen,nbits,alen=struct.unpack_from('<4sBBBBIII',buf,off);off+=FRAME_HEAD
    if magic!=MAGIC:raise RuntimeError('symbol frame magic')
    meta=buf[off:off+mlen];off+=mlen;astore=buf[off:off+alen];off+=alen
    if off!=len(buf):raise RuntimeError('symbol frame trailing')
    hist=meta_decode(meta,zf);state=state_from_hist(hist);bits=m.D.decompress(astore) if af else astore;dec=MultiDecoder(bits,nbits);K=np.zeros(shape,np.int32);fam=FAMILIES[fid]
    for t in range(shape[1]):
        for c in range(shape[0]):
            q=ctx(K,c,t,fam)
            if q not in state:raise RuntimeError(('unknown ctx',fam,q,c,t))
            syms,idx,fw=state[q];total=fw.total()
            if total<=0:raise RuntimeError(('context exhausted',fam,q))
            if len(syms)==1:i=0
            else:
                target=dec.target(total);i=fw.find(target)
                # If only one remaining symbol has all mass, no arithmetic bits were emitted.
                if fw.a[i]<total:dec.consume(fw.sum(i),fw.a[i],total)
            v=syms[i];K[c,t]=v;fw.update(i,-1)
    if any(fw.total()!=0 for _,_,fw in state.values()):raise RuntimeError('hist not exhausted')
    return K

def validate(X,eps,mb,cd,R,K,fid):
    buf,detail=encode_family(K,fid);Kd=decode_frame(buf,K.shape)
    if not np.array_equal(Kd,K):raise RuntimeError(('symbol K mismatch',FAMILIES[fid]))
    Rd=np.zeros_like(R)
    for c in range(K.shape[0]):
        for t in range(K.shape[1]):Rd[c,t]=g.ar.predict_hist(Rd,c,t,cd,g.P,'shared')+base.STEP*int(Kd[c,t])
    if not np.array_equal(Rd,R):raise RuntimeError(('symbol AR replay',FAMILIES[fid]))
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('symbol hard',me,eps))
    total=mb+len(buf)+base.HEADER
    return {'family':FAMILIES[fid],'bytes':int(total),'bps':8*total/X.size,'model_bytes':int(mb),'address_bytes':len(buf),'maxerr':me,'detail':detail}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);mb,cd,R,K=base.build_ar32(X);ab,arep,AK,ad=ac.autocomplexity_frame(K)
    if not np.array_equal(AK,K):raise RuntimeError('auto baseline replay')
    auto={'bytes':int(mb+ab+base.HEADER),'bps':8*(mb+ab+base.HEADER)/X.size,'address_bytes':int(ab),'rep':arep}
    rows=[]
    for fid in range(len(FAMILIES)):
        z=validate(X,eps,mb,cd,R,K,fid);z['gain_vs_auto']=auto['bytes']/z['bytes'];z['gain_vs_sz3']=szb/z['bytes'];rows.append(z);print(json.dumps({k:v for k,v in z.items() if k!='detail'},indent=2),flush=True)
    rows.sort(key=lambda x:x['bytes']);best=rows[0]
    out={'region':'hard','shape':[g.C,g.T],'samples':int(X.size),'global_std':std,'eps':eps,'step':base.STEP,'sz3':{'bytes':int(szb),'bps':8*szb/X.size,'orientation':ori},'ar32_autocomplexity':auto,'families':list(FAMILIES),'rows':rows,'best':best,'scope':'Exact whole-symbol type-class constrained address on the frozen incumbent AR32 K field. Decoder-known causal state is built only from already decoded innovations and fixed channel coordinates. For each public context family the encoder transmits the complete sparse histogram of K symbols per context (all counts fully charged and optionally Zstd-compressed), then arithmetic-ranks the actual time-major K sequence without replacement inside those context type classes. Because contexts using current-left K depend on decoded symbols, the decoder regenerates context state causally and every transmitted histogram must exhaust exactly. The arithmetic stream, context-family selector, sparse histogram metadata and framing are real bytes. Decoder reconstructs identical K, identical AR32 R and verifies the unchanged source hard error. This is the exact finite-state version of using decoder-known state to restrict the candidate universe; historical conditional-entropy numbers are diagnostics only and are not counted here.'}
    json.dump(out,open('imperial_ar32_symbol_typeclass_address.json','w'),indent=2)
    print(json.dumps({'summary':{'best_family':best['family'],'best_bytes':best['bytes'],'auto_bytes':auto['bytes'],'sz3_bytes':int(szb),'gain_auto':auto['bytes']/best['bytes'],'gain_sz3':int(szb)/best['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
