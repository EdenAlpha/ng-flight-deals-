import sys,json,struct
import h5py,numpy as np
import imperial_ar4_rich_adaptive_context_address as rich
import imperial_defect_restricted_rank_address as rr
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

a=rich.a
a.P=1
a.TRAIN=64
HEADER=32
SELECTOR=1

def put_uvar(out,x):rr.put_uvar(out,int(x))
def get_uvar(buf,p):return rr.get_uvar(buf,p)

def pack_hist(counts):
    counts=np.asarray(counts,np.int64);nz=np.flatnonzero(counts)
    # mode0: all counts as varints
    b0=bytearray();
    for x in counts:put_uvar(b0,int(x))
    # mode1: sparse delta-symbol/count pairs
    b1=bytearray();put_uvar(b1,len(nz));prev=-1
    for i in nz:
        put_uvar(b1,int(i)-prev-1);put_uvar(b1,int(counts[i]));prev=int(i)
    candidates=[]
    for mode,raw in ((0,bytes(b0)),(1,bytes(b1))):
        z=m.Z.compress(raw)
        if len(z)<len(raw):c=1;store=z
        else:c=0;store=raw
        candidates.append((len(store),mode,c,store))
    _,mode,c,store=min(candidates,key=lambda x:x[0])
    return struct.pack('<BBI',mode,c,len(store))+store,{'hist_mode':mode,'hist_compressed':c,'hist_bytes':len(store)+6,'nonzero_symbols':int(len(nz))}

def unpack_hist(buf,off,M,total):
    mode,c,n=struct.unpack_from('<BBI',buf,off);off+=6;store=buf[off:off+n];off+=n
    raw=m.D.decompress(store) if c else store;p=0;counts=np.zeros(M,np.int64)
    if mode==0:
        for i in range(M):counts[i],p=get_uvar(raw,p)
    elif mode==1:
        nn,p=get_uvar(raw,p);idx=-1
        for _ in range(nn):
            d,p=get_uvar(raw,p);v,p=get_uvar(raw,p);idx+=int(d)+1
            if idx<0 or idx>=M:raise RuntimeError(('hist symbol',idx,M))
            counts[idx]=int(v)
    else:raise RuntimeError(('hist mode',mode))
    if p!=len(raw):raise RuntimeError(('hist trailing',p,len(raw)))
    if int(counts.sum())!=total:raise RuntimeError(('hist total',int(counts.sum()),total))
    return counts,off

class SumTree:
    def __init__(self,counts):
        self.M=len(counts);s=1
        while s<self.M:s<<=1
        self.S=s;self.t=[0]*(2*s)
        for i,x in enumerate(counts):self.t[s+i]=int(x)
        for i in range(s-1,0,-1):self.t[i]=self.t[i<<1]+self.t[i<<1|1]
    def branch(self,node):return self.t[node<<1],self.t[node<<1|1]
    def dec(self,sym):
        i=self.S+int(sym)
        if self.t[i]<=0:raise RuntimeError(('decrement empty',sym))
        self.t[i]-=1;i>>=1
        while i:self.t[i]=self.t[i<<1]+self.t[i<<1|1];i>>=1

def encode_sequence(U,counts):
    tr=SumTree(counts);ae=rr.ArithEncoder();M=len(counts);S=tr.S
    for sym0 in np.asarray(U,np.uint64).ravel(order='C'):
        sym=int(sym0);node=1;lo=0;hi=S
        while node<S:
            zl,or_=tr.branch(node);mid=(lo+hi)//2
            if sym<mid:
                if or_ and zl:ae.encode(0,zl,or_)
                elif zl<=0:raise RuntimeError(('impossible left',sym,lo,hi))
                node=node<<1;hi=mid
            else:
                if or_ and zl:ae.encode(1,zl,or_)
                elif or_<=0:raise RuntimeError(('impossible right',sym,lo,hi))
                node=node<<1|1;lo=mid
        if lo!=sym:raise RuntimeError(('tree leaf',lo,sym))
        tr.dec(sym)
    raw,nbits=ae.finish();z=m.Z.compress(raw)
    if len(z)<len(raw):am=1;store=z
    else:am=0;store=raw
    return struct.pack('<BII',am,int(nbits),len(store))+store,{'arith_bits':int(nbits),'arith_bytes':len(store),'arith_compressed':am,'arith_frame_bytes':len(store)+9}

def decode_sequence(buf,off,counts,shape):
    am,nbits,n=struct.unpack_from('<BII',buf,off);off+=9;store=buf[off:off+n];off+=n
    raw=m.D.decompress(store) if am else store;ad=rr.ArithDecoder(raw,nbits);tr=SumTree(counts);N=int(np.prod(shape));out=np.empty(N,np.uint64);S=tr.S
    for q in range(N):
        node=1;lo=0;hi=S
        while node<S:
            zl,or_=tr.branch(node);mid=(lo+hi)//2
            if zl<=0:b=1
            elif or_<=0:b=0
            else:b=ad.decode(zl,or_)
            if b==0:node=node<<1;hi=mid
            else:node=node<<1|1;lo=mid
        if lo>=tr.M:raise RuntimeError(('decoded pad symbol',lo,tr.M))
        out[q]=lo;tr.dec(lo)
    return out.reshape(shape),off

def hist_rank_frame(K):
    K=np.asarray(K,np.int32);U=m.zig(K);mx=int(U.max()) if U.size else 0;M=mx+1
    counts=np.bincount(U.ravel().astype(np.int64),minlength=M).astype(np.int64)
    hblob,hd=pack_hist(counts);ablob,ad=encode_sequence(U,counts.copy())
    out=bytearray(struct.pack('<4sHHH',b'HSR1',K.shape[0],K.shape[1],M));out.extend(hblob);out.extend(ablob);buf=bytes(out)
    off=0;magic,nc,nt,M2=struct.unpack_from('<4sHHH',buf,off);off+=10
    if magic!=b'HSR1' or (nc,nt)!=K.shape or M2!=M:raise RuntimeError('hist rank header')
    cd,off=unpack_hist(buf,off,M,K.size);Ud,off=decode_sequence(buf,off,cd,K.shape)
    if off!=len(buf):raise RuntimeError(('frame trailing',off,len(buf)))
    Kd=m.unzig(Ud).astype(np.int32)
    if not np.array_equal(Kd,K):raise RuntimeError('hist rank K replay')
    return len(buf),'symbol_histogram_rank',Kd,{**hd,**ad,'symbols':M,'max_u':mx,'frame_bytes':len(buf)}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);old=g.ar32_baseline(X,eps);mb,cd,R,K,me=a.build_ar8(X,eps)
    richb,_,richK,richd=a.hybrid_frame(K);hb,hn,hK,hd=hist_rank_frame(K)
    if not np.array_equal(richK,K) or not np.array_equal(hK,K):raise RuntimeError('K replay')
    richme=a.replay(X,eps,cd,richK,R);hme=a.replay(X,eps,cd,hK,R)
    richt=int(mb)+int(richb)+HEADER+SELECTOR;ht=int(mb)+int(hb)+HEADER+SELECTOR
    chosen='symbol_histogram_rank' if ht<richt else 'rich_bitplanes';best=min(ht,richt)
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'order':1,'train':64,'step':267,'model_bytes':int(mb),'rich_bitplanes':{'bytes':richt,'payload_bytes':int(richb),'maxerr':richme,'detail':richd},'symbol_histogram_rank':{'bytes':ht,'payload_bytes':int(hb),'maxerr':hme,'detail':hd},'chosen':chosen,'best_bytes':best,'delta_symbol_vs_rich':ht-richt,'old_ar32':old,'sz3':{'bytes':int(szb),'orientation':ori},'gain_vs_old_ar32':old['bytes']/best,'gain_vs_sz3':szb/best,'scope':'Exact Complexity-Weapon whole-symbol rank test on AR1/train64/step267. The proven rich bitplane address is reproduced as a strict floor. The alternative transmits the exact zigzag-K histogram, then arithmetic-ranks the complete symbol sequence among all permutations having that histogram by decrementing the decoder-known remaining symbol counts after every decoded symbol. The histogram itself is physically stored using the smaller of dense/sparse varints with optional Zstd and is fully charged. No ideal entropy or unmaterialized multinomial rate counts. The complete K field is independently decoded, AR1 is causally replayed, and the unchanged source hard-error bound is verified.'}
    json.dump(out,open('imperial_ar1_symbol_histogram_rank.json','w'),indent=2)
    print(json.dumps({'summary':{'rich':richt,'symbol_hist_rank':ht,'delta':ht-richt,'chosen':chosen,'best':best,'old_ar32':old['bytes'],'sz3':int(szb),'gain_vs_old_ar32':old['bytes']/best,'gain_vs_sz3':szb/best,'hist':hd}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
