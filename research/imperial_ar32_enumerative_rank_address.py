import json,sys,math
from collections import Counter
import h5py,numpy as np
import imperial_dyadic_shared_resonator as ar
import imperial_decoder_phase_automaton as m
import imperial_persistent_ar32_full_array_jit as aj

T0=14488;C0=512;C=32;T=4096;TRAIN=1024;P=32;STEP=267;OUTER_HEADER=32
MAGIC=b'ERA1'
TILINGS=((32,4096),(32,2048),(32,1024),(32,512),(32,256),(16,1024),(16,512),(16,256),(8,1024),(8,512),(8,256),(4,1024),(4,512),(4,256),(2,1024),(2,512),(1,1024),(1,512))
aj.m.P=32;aj.m.m.STEP=STEP

# ----- integer framing -----
def uvar(v):
    v=int(v);o=bytearray()
    if v<0:raise ValueError(v)
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
        if s>63:raise RuntimeError('uvar overflow')

def zig(v):
    v=int(v);return 2*v if v>=0 else -2*v-1

def unzig(u):
    u=int(u);return u//2 if u%2==0 else -(u//2)-1

# ----- Fenwick tree for exact remaining-count cumulative frequencies -----
class Fenwick:
    def __init__(self,a):
        self.n=len(a);self.t=[0]*(self.n+1)
        for i,v in enumerate(a):
            j=i+1
            while j<=self.n:self.t[j]+=int(v);j+=j&-j
    def prefix(self,i):
        s=0
        while i:s+=self.t[i];i-=i&-i
        return s
    def total(self):return self.prefix(self.n)
    def add(self,i,d):
        j=i+1
        while j<=self.n:self.t[j]+=d;j+=j&-j
    def find_order(self,value):
        idx=0;s=0;bit=1<<(self.n.bit_length()-1)
        while bit:
            q=idx+bit
            if q<=self.n and s+self.t[q]<=value:idx=q;s+=self.t[q]
            bit>>=1
        if idx>=self.n:raise RuntimeError(('find order',value,self.total()))
        return idx,s

class BitOut:
    def __init__(self):self.a=[]
    def put(self,b):self.a.append(1 if b else 0)
    def finish(self):
        if not self.a:return b''
        return np.packbits(np.asarray(self.a,np.uint8),bitorder='big').tobytes()
class BitIn:
    def __init__(self,b):self.b=b;self.p=0
    def get(self):
        if self.p>=8*len(self.b):self.p+=1;return 0
        z=(self.b[self.p>>3]>>(7-(self.p&7)))&1;self.p+=1;return z

STATE=32;FULL=1<<STATE;HALF=FULL>>1;QUARTER=HALF>>1;THREE=3*QUARTER

def arithmetic_rank_encode(seq,symbols,init_counts):
    seq=np.asarray(seq,np.int32).ravel();symbols=[int(x) for x in symbols];counts=[int(x) for x in init_counts]
    if len(symbols)<=1:return b''
    mp={s:i for i,s in enumerate(symbols)};fw=Fenwick(counts);low=0;high=FULL-1;pending=0;bo=BitOut()
    def emit(bit,n):
        bo.put(bit)
        for _ in range(n):bo.put(1-bit)
    for sv in seq:
        i=mp[int(sv)];total=fw.total();cl=fw.prefix(i);ch=cl+counts[i];rng=high-low+1
        high=low+(rng*ch//total)-1;low=low+(rng*cl//total)
        while True:
            if high<HALF:emit(0,pending);pending=0
            elif low>=HALF:emit(1,pending);pending=0;low-=HALF;high-=HALF
            elif low>=QUARTER and high<THREE:pending+=1;low-=QUARTER;high-=QUARTER
            else:break
            low=(low<<1)&(FULL-1);high=((high<<1)|1)&(FULL-1)
        counts[i]-=1;fw.add(i,-1)
    pending+=1
    if low<QUARTER:emit(0,pending)
    else:emit(1,pending)
    return bo.finish()

def arithmetic_rank_decode(blob,symbols,init_counts,n):
    symbols=[int(x) for x in symbols];counts=[int(x) for x in init_counts]
    if len(symbols)==1:return np.full(n,symbols[0],np.int32)
    fw=Fenwick(counts);bi=BitIn(blob);low=0;high=FULL-1;code=0
    for _ in range(STATE):code=((code<<1)|bi.get())&(FULL-1)
    out=np.empty(n,np.int32)
    for k in range(n):
        total=fw.total();rng=high-low+1;value=((code-low+1)*total-1)//rng;i,cl=fw.find_order(value);ch=cl+counts[i]
        high=low+(rng*ch//total)-1;low=low+(rng*cl//total)
        while True:
            if high<HALF:pass
            elif low>=HALF:low-=HALF;high-=HALF;code-=HALF
            elif low>=QUARTER and high<THREE:low-=QUARTER;high-=QUARTER;code-=QUARTER
            else:break
            low=(low<<1)&(FULL-1);high=((high<<1)|1)&(FULL-1);code=((code<<1)|bi.get())&(FULL-1)
        out[k]=symbols[i];counts[i]-=1;fw.add(i,-1)
    if fw.total()!=0:raise RuntimeError(('rank counts remain',fw.total()))
    return out

# ----- self-contained tile histogram + exact rank -----
def encode_tile(A):
    seq=np.asarray(A,np.int32).ravel();sy,cnt=np.unique(seq,return_counts=True);sy=[int(x) for x in sy];cnt=[int(x) for x in cnt]
    payload=arithmetic_rank_encode(seq,sy,cnt)
    h=bytearray();h+=uvar(len(sy));h+=uvar(zig(sy[0]))
    for i in range(1,len(sy)):h+=uvar(sy[i]-sy[i-1])
    for n in cnt[:-1]:h+=uvar(n)
    h+=uvar(len(payload));h+=payload
    theory=(math.lgamma(len(seq)+1)-sum(math.lgamma(n+1) for n in cnt))/math.log(2)
    return bytes(h),{'symbols':len(sy),'header_payload_bytes':len(h),'rank_payload_bytes':len(payload),'ideal_multinomial_bits':theory}

def decode_tile(buf,pos,n):
    ns,pos=read_uvar(buf,pos);u,pos=read_uvar(buf,pos);sy=[unzig(u)]
    for _ in range(1,ns):g,pos=read_uvar(buf,pos);sy.append(sy[-1]+g)
    cnt=[];used=0
    for _ in range(ns-1):q,pos=read_uvar(buf,pos);cnt.append(int(q));used+=int(q)
    last=n-used
    if last<=0 and ns>1:raise RuntimeError(('bad last count',last,n,used))
    cnt.append(last)
    bl,pos=read_uvar(buf,pos)
    if pos+bl>len(buf):raise RuntimeError('tile payload eof')
    out=arithmetic_rank_decode(buf[pos:pos+bl],sy,cnt,n);pos+=bl
    return out,pos

def build_address(K,cb,tb):
    K=np.asarray(K,np.int32);raw=bytearray(MAGIC);raw+=uvar(K.shape[0])+uvar(K.shape[1])+uvar(cb)+uvar(tb);tiles=[]
    for c0 in range(0,K.shape[0],cb):
        c1=min(K.shape[0],c0+cb)
        for t0 in range(0,K.shape[1],tb):
            t1=min(K.shape[1],t0+tb);fr,st=encode_tile(K[c0:c1,t0:t1]);raw+=fr;st.update({'c0':c0,'c1':c1,'t0':t0,'t1':t1});tiles.append(st)
    raw=bytes(raw);z=m.Z.compress(raw)
    if len(z)<len(raw):container=b'\x01'+z;rep='zstd'
    else:container=b'\x00'+raw;rep='raw'
    return container,{'raw_bytes':len(raw),'container_bytes':len(container),'outer_rep':rep,'tiles':tiles,'ideal_bits':sum(x['ideal_multinomial_bits'] for x in tiles),'rank_payload_bytes':sum(x['rank_payload_bytes'] for x in tiles)}

def decode_address(container):
    if not container:raise RuntimeError('empty address')
    raw=m.D.decompress(container[1:]) if container[0]==1 else bytes(container[1:])
    if raw[:4]!=MAGIC:raise RuntimeError('magic')
    pos=4;Cc,pos=read_uvar(raw,pos);Tt,pos=read_uvar(raw,pos);cb,pos=read_uvar(raw,pos);tb,pos=read_uvar(raw,pos);K=np.empty((Cc,Tt),np.int32)
    for c0 in range(0,Cc,cb):
        c1=min(Cc,c0+cb)
        for t0 in range(0,Tt,tb):
            t1=min(Tt,t0+tb);n=(c1-c0)*(t1-t0);seq,pos=decode_tile(raw,pos,n);K[c0:c1,t0:t1]=seq.reshape(c1-c0,t1-t0)
    if pos!=len(raw):raise RuntimeError(('address trailing',pos,len(raw)))
    return K

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic']
        if tuple(d.shape)!=(30000,6912):raise RuntimeError(('shape',d.shape))
        _,std=m.stats(d);eps=.1*std;X=np.asarray(d[T0:T0+T,C0:C0+C],np.float64).T
    co=ar.fit_shared(X[:,:TRAIN],P);mb,cd=ar.model_frame(co);R,K=aj.build(X,cd);fr=m.encode_k(K);Kd=np.asarray(fr[2],np.int32);Rd=aj.decode(Kd,cd)
    if not np.array_equal(Rd,R):raise RuntimeError('baseline replay')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('baseline hard',me,eps))
    baseline=int(mb)+int(fr[0])+OUTER_HEADER;szb,ori=m.szrun(X,eps);rows=[]
    for cb,tb in TILINGS:
        container,st=build_address(K,cb,tb);KD=decode_address(container)
        if not np.array_equal(KD,K):raise RuntimeError(('rank K mismatch',cb,tb))
        R2=aj.decode(KD,cd)
        if not np.array_equal(R2,R):raise RuntimeError(('rank AR replay',cb,tb))
        me2=float(np.max(np.abs(X-R2.astype(np.float64))))
        if me2>eps*(1+5e-6):raise RuntimeError(('rank hard',cb,tb,me2,eps))
        total=int(mb)+len(container)+OUTER_HEADER
        row={'channel_block':cb,'time_block':tb,'tiles':len(st['tiles']),'bytes':total,'bps':8*total/X.size,'model_bytes':int(mb),'address_bytes':len(container),'address_raw_bytes':st['raw_bytes'],'outer_rep':st['outer_rep'],'rank_payload_bytes':st['rank_payload_bytes'],'ideal_multinomial_bytes':st['ideal_bits']/8,'address_over_ideal_bytes':len(container)-st['ideal_bits']/8,'gain_vs_ar32':baseline/total,'gain_vs_sz3':szb/total,'maxerr':me2,'median_symbols_per_tile':float(np.median([q['symbols'] for q in st['tiles']])),'max_symbols_per_tile':max(q['symbols'] for q in st['tiles'])};rows.append(row);print(json.dumps(row,indent=2),flush=True)
    rows.sort(key=lambda r:r['bytes']);best=rows[0]
    out={'region':'hard','t0':T0,'c0':C0,'shape':[C,T],'samples':int(X.size),'global_std':std,'eps':eps,'ar_order':P,'step':STEP,'ar32':{'bytes':baseline,'bps':8*baseline/X.size,'innovation_bytes':int(fr[0]),'innovation_rep':fr[1],'model_bytes':int(mb),'maxerr':me,'zero_fraction':float(np.mean(K==0)),'k_std':float(K.std()),'min_k':int(K.min()),'max_k':int(K.max())},'sz3':{'bytes':int(szb),'bps':8*szb/X.size,'orientation':ori},'tilings':[list(x) for x in TILINGS],'best':best,'rows':rows,'scope':'Actual finite constrained-universe rank codec for the exact incumbent AR32 step267 innovation field. Each spatial/temporal tile transmits its signed-symbol support and counts, then arithmetic-codes the tile sequence using probabilities equal to the exact remaining symbol counts without replacement. Therefore every decoded prefix shrinks the candidate universe deterministically; the probability product is exactly the reciprocal multinomial class size, apart from arithmetic-coder termination/framing. This is a real rank stream, not an entropy estimate or summed heuristic restriction. The encoder searches multiple public tile partitions so local nonstationarity can be purchased only when histogram bits pay for themselves. Histogram values/counts and tile framing are fully serialized; the complete address optionally receives one outer Zstd pass. Decoder byte-parses every tile, reconstructs exact K, replays the full AR32 state exactly and verifies the unchanged source hard-error bound. Matched incumbent encode_k and SZ3 are rerun on the same hard 32x4096 object.'}
    json.dump(out,open('imperial_ar32_enumerative_rank_address.json','w'),indent=2)
    print(json.dumps({'summary':{'rank_bytes':best['bytes'],'ar32_bytes':baseline,'sz3_bytes':int(szb),'gain_ar32':best['gain_vs_ar32'],'gain_sz3':best['gain_vs_sz3'],'tile':[best['channel_block'],best['time_block']],'address_bytes':best['address_bytes'],'ideal_multinomial_bytes':best['ideal_multinomial_bytes'],'over_ideal':best['address_over_ideal_bytes'],'outer':best['outer_rep']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
