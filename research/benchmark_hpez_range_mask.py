import bisect, json, os, subprocess, numpy as np

CENTER=32768
RAW=64*64*512*4
HEADER=64

class BitWriter:
    def __init__(self): self.out=bytearray(); self.cur=0; self.n=0
    def bit(self,b):
        self.cur=(self.cur<<1)|(1 if b else 0); self.n+=1
        if self.n==8: self.out.append(self.cur); self.cur=0; self.n=0
    def finish(self):
        if self.n: self.out.append(self.cur<<(8-self.n)); self.cur=0; self.n=0
        return bytes(self.out)

class ArithmeticEncoder:
    HALF=1<<31; Q1=1<<30; Q3=3<<30; MAX=(1<<32)-1
    def __init__(self): self.lo=0; self.hi=self.MAX; self.follow=0; self.w=BitWriter()
    def emit(self,b):
        self.w.bit(b)
        while self.follow:
            self.w.bit(1-b); self.follow-=1
    def update(self,cl,ch,total):
        r=self.hi-self.lo+1
        self.hi=self.lo+(r*ch//total)-1
        self.lo=self.lo+(r*cl//total)
        while True:
            if self.hi < self.HALF:
                self.emit(0)
            elif self.lo >= self.HALF:
                self.emit(1); self.lo-=self.HALF; self.hi-=self.HALF
            elif self.lo >= self.Q1 and self.hi < self.Q3:
                self.follow+=1; self.lo-=self.Q1; self.hi-=self.Q1
            else: break
            self.lo=(self.lo<<1)&self.MAX; self.hi=((self.hi<<1)&self.MAX)|1
    def finish(self):
        self.follow+=1
        self.emit(0 if self.lo < self.Q1 else 1)
        return self.w.finish()

class BitReader:
    def __init__(self,b): self.b=b; self.i=0
    def bit(self):
        if self.i >= len(self.b)*8: self.i+=1; return 0
        v=(self.b[self.i>>3]>>(7-(self.i&7)))&1; self.i+=1; return v

class ArithmeticDecoder:
    HALF=1<<31; Q1=1<<30; Q3=3<<30; MAX=(1<<32)-1
    def __init__(self,b):
        self.lo=0; self.hi=self.MAX; self.r=BitReader(b); self.code=0
        for _ in range(32): self.code=((self.code<<1)|self.r.bit())&self.MAX
    def scaled(self,total):
        rg=self.hi-self.lo+1
        return ((self.code-self.lo+1)*total-1)//rg
    def update(self,cl,ch,total):
        rg=self.hi-self.lo+1
        self.hi=self.lo+(rg*ch//total)-1
        self.lo=self.lo+(rg*cl//total)
        while True:
            if self.hi < self.HALF: pass
            elif self.lo >= self.HALF:
                self.lo-=self.HALF; self.hi-=self.HALF; self.code-=self.HALF
            elif self.lo >= self.Q1 and self.hi < self.Q3:
                self.lo-=self.Q1; self.hi-=self.Q1; self.code-=self.Q1
            else: break
            self.lo=(self.lo<<1)&self.MAX; self.hi=((self.hi<<1)&self.MAX)|1; self.code=((self.code<<1)&self.MAX)|self.r.bit()
    def binary(self,f0,f1):
        total=f0+f1; s=self.scaled(total)
        if s < f0: sym=0; cl=0; ch=f0
        else: sym=1; cl=f0; ch=total
        self.update(cl,ch,total); return sym
    def symbol(self,cum):
        total=cum[-1]; s=self.scaled(total)
        k=bisect.bisect_right(cum,s)-1
        self.update(cum[k],cum[k+1],total); return k

def z(b):
    return subprocess.run(['zstd','-q','-f','-19','-T0','-c'],input=b,stdout=subprocess.PIPE,check=True).stdout

def zd(b):
    return subprocess.run(['zstd','-q','-d','-c'],input=b,stdout=subprocess.PIPE,check=True).stdout

def contexts(mask):
    xp=np.zeros(mask.shape,np.uint8); yp=np.zeros(mask.shape,np.uint8); tp=np.zeros(mask.shape,np.uint8)
    xp[1:,:,:]=mask[:-1,:,:]; yp[:,1:,:]=mask[:,:-1,:]; tp[:,:,1:]=mask[:,:,:-1]
    return ((xp<<2)|(yp<<1)|tp).astype(np.uint8)

def class_arrays(Q):
    out=[]
    for level in [5,4,3,2,1]:
        s=1<<(level-1); step=2*s; sh=(64//step,64//step,512//step)
        pat=0
        for pi in [0,1]:
            for pj in [0,1]:
                for pt in [0,1]:
                    if pi==pj==pt==0: continue
                    pat+=1
                    A=Q[pi*s:pi*s+sh[0]*step:step,pj*s:pj*s+sh[1]*step:step,pt*s:pt*s+sh[2]*step:step]
                    assert A.shape==sh
                    out.append((level,pat,(pi,pj,pt),s,step,A.copy()))
    return out

def build_models(root_ids,classes,alphabet):
    K=len(alphabet); root=np.bincount(root_ids,minlength=K).astype('<u4')
    masks=[]; vals=[]
    for _,_,_,_,_,A in classes:
        m=(A!=CENTER).astype(np.uint8); c=contexts(m)
        mc=np.zeros((8,2),np.uint32)
        for k in range(8):
            x=m[c==k]; mc[k,0]=np.count_nonzero(x==0); mc[k,1]=np.count_nonzero(x==1)
        ids=np.searchsorted(alphabet,A[m!=0]).astype(np.int64)
        vc=np.bincount(ids,minlength=K).astype(np.uint32)
        masks.append(mc); vals.append(vc)
    masks=np.stack(masks).astype('<u4'); vals=np.stack(vals).astype('<u4')
    raw=(np.array([K,len(classes)],dtype='<u4').tobytes()+alphabet.astype('<i4').tobytes()+root.tobytes()+masks.tobytes()+vals.tobytes())
    return root,masks,vals,raw

def parse_models(raw):
    pos=0; hdr=np.frombuffer(raw[pos:pos+8],dtype='<u4'); pos+=8; K,C=map(int,hdr)
    alphabet=np.frombuffer(raw[pos:pos+4*K],dtype='<i4').copy(); pos+=4*K
    root=np.frombuffer(raw[pos:pos+4*K],dtype='<u4').copy(); pos+=4*K
    masks=np.frombuffer(raw[pos:pos+4*C*8*2],dtype='<u4').reshape(C,8,2).copy(); pos+=4*C*8*2
    vals=np.frombuffer(raw[pos:pos+4*C*K],dtype='<u4').reshape(C,K).copy(); pos+=4*C*K
    if pos!=len(raw): raise RuntimeError('model parse length')
    return alphabet,root,masks,vals

def cumulative(counts):
    # Laplace +1 keeps every symbol legal while remaining fully transmitted/reproducible.
    f=np.asarray(counts,dtype=np.int64)+1
    return np.concatenate(([0],np.cumsum(f))).astype(np.int64).tolist()

meta=json.load(open('data/forge_subcube_meta.json')); eps=float(meta['eps_10pct_std'])
X=np.fromfile('data/forge_subcube_f32.bin','<f4'); R=np.fromfile('stock_rec.bin','<f4'); maxerr=float(np.max(np.abs(X-R)))
if maxerr>eps*1.00001: raise SystemExit('stock error violation')
q=np.fromfile('hpez_final_quant_inds.bin',np.int32); coords=np.fromfile('hpez_final_quant_coords_u64.bin',np.uint64)
if q.size!=64*64*512 or coords.size!=q.size or np.unique(coords).size!=q.size: raise SystemExit('bad dumps')
phys=np.empty_like(q);phys[coords.astype(np.int64)]=q;Q=phys.reshape(64,64,512)
alphabet=np.unique(q).astype(np.int32); K=len(alphabet)
root=Q[0::32,0::32,0::32]; root_ids=np.searchsorted(alphabet,root.ravel()).astype(np.int64)
classes=class_arrays(Q)
root_counts,mask_counts,val_counts,model_raw=build_models(root_ids,classes,alphabet)
model_c=z(model_raw); model_rt=zd(model_c)
a2,root2,mask2,val2=parse_models(model_rt)
if not np.array_equal(a2,alphabet): raise SystemExit('alphabet model mismatch')

enc=ArithmeticEncoder(); root_cum=cumulative(root2)
for sid in root_ids: enc.update(root_cum[int(sid)],root_cum[int(sid)+1],root_cum[-1])
for ci,(_,_,_,_,_,A) in enumerate(classes):
    m=(A!=CENTER).astype(np.uint8); ctx=contexts(m)
    for bit,c in zip(m.ravel(),ctx.ravel()):
        f0=int(mask2[ci,int(c),0])+1; f1=int(mask2[ci,int(c),1])+1
        if int(bit)==0: enc.update(0,f0,f0+f1)
        else: enc.update(f0,f0+f1,f0+f1)
    vcum=cumulative(val2[ci]); ids=np.searchsorted(alphabet,A[m!=0]).astype(np.int64)
    for sid in ids: enc.update(vcum[int(sid)],vcum[int(sid)+1],vcum[-1])
arith=enc.finish()

# Decoder: models come only from transmitted compressed model frame, and contexts only from already decoded masks.
dec=ArithmeticDecoder(arith); Qd=np.full(Q.shape,CENTER,np.int32)
for a in range(0,64,32):
    for b in range(0,64,32):
        for c in range(0,512,32):
            sid=dec.symbol(root_cum); Qd[a,b,c]=alphabet[sid]
for ci,(level,pat,(pi,pj,pt),s,step,Aref) in enumerate(classes):
    sh=Aref.shape; m=np.zeros(sh,np.uint8)
    # C-order is a,b,c; x/y/t predecessors are already decoded.
    for a in range(sh[0]):
        for b in range(sh[1]):
            for c in range(sh[2]):
                cx=(int(m[a-1,b,c])<<2 if a else 0)|(int(m[a,b-1,c])<<1 if b else 0)|(int(m[a,b,c-1]) if c else 0)
                f0=int(mask2[ci,cx,0])+1; f1=int(mask2[ci,cx,1])+1
                m[a,b,c]=dec.binary(f0,f1)
    vcum=cumulative(val2[ci]); A=np.full(sh,CENTER,np.int32)
    for a in range(sh[0]):
        for b in range(sh[1]):
            for c in range(sh[2]):
                if m[a,b,c]: A[a,b,c]=alphabet[dec.symbol(vcum)]
    Qd[pi*s:pi*s+sh[0]*step:step,pj*s:pj*s+sh[1]*step:step,pt*s:pt*s+sh[2]*step:step]=A

exact=bool(np.array_equal(Qd,Q))
if not exact:
    idx=np.argwhere(Qd!=Q)[0].tolist(); raise SystemExit(f'decoder mismatch at {idx}')
prefix=open('hpez_prefix.bin','rb').read(); prefix_c=z(prefix)
total=len(prefix_c)+len(model_c)+len(arith)+HEADER
stock=os.path.getsize('stock.hpez')
out={'raw_bytes':RAW,'eps':eps,'stock_hpez_bytes':stock,'stock_hpez_ratio':RAW/stock,'stock_hpez_maxerr':maxerr,
     'prefix_raw':len(prefix),'prefix_z':len(prefix_c),'model_raw':len(model_raw),'model_z':len(model_c),'arithmetic_bytes':len(arith),
     'header_bytes':HEADER,'total_bytes':total,'ratio':RAW/total,'gain_vs_stock_pct':100*((RAW/total)/(RAW/stock)-1),
     'alphabet_size':K,'classes':len(classes),'decoder_exact':exact,
     'method':'single arithmetic stream: root symbols, then for each dyadic level/parity class an 8-state causal occupancy mask followed by static noncenter-value arithmetic symbols; all frequency tables transmitted and Zstd-compressed'}
json.dump(out,open('forge_hpez_range_mask_results.json','w'),indent=2); print('RANGEMASK',json.dumps(out,indent=2),flush=True)
