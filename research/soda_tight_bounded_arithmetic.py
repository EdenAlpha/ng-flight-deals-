import bisect,json,os,struct,sys
import numpy as np

# Reuse PR #176's exact tight-fidelity semantics, geometry, outlier dictionary,
# Rice magnitude option and audited lossless backend menu.  This experiment
# changes only the inter-run gap-minus-2 entropy representation.
src=open('research/soda_tight_rice_frames.py').read().split('\ndef main(path,frac):')[0]
exec(compile(src,'soda_tight_rice_frames.py','exec'),globals())

BA_MAGIC=b'BARITH01'
BA_HDR='<8sBBBBB4I12B12Q'
BA_HS=struct.calcsize(BA_HDR)
FULL=1<<32;HALF=1<<31;Q1=1<<30;Q3=3<<30
CUTS=(3,7,15,31,63)

class BitWriter:
    def __init__(self):self.buf=bytearray();self.acc=0;self.n=0;self.bits=0
    def bit(self,b):
        self.acc|=(int(b)&1)<<self.n;self.n+=1;self.bits+=1
        if self.n==8:self.buf.append(self.acc);self.acc=0;self.n=0
    def finish(self):
        if self.n:self.buf.append(self.acc);self.acc=0;self.n=0
        return bytes(self.buf),int(self.bits)
class BitReader:
    def __init__(self,b):self.b=memoryview(b);self.i=0;self.acc=0;self.n=0
    def bit(self):
        if not self.n:
            if self.i>=len(self.b):return 0
            self.acc=int(self.b[self.i]);self.i+=1;self.n=8
        v=self.acc&1;self.acc>>=1;self.n-=1;return v

def vput(out,x):
    x=int(x)
    if x<0:raise RuntimeError(('negative varint',x))
    while x>=128:out.append((x&127)|128);x>>=7
    out.append(x)
def vget(b,p):
    x=0;s=0
    while True:
        if p>=len(b):raise RuntimeError('varint EOF')
        q=int(b[p]);p+=1;x|=(q&127)<<s
        if q<128:return x,p
        s+=7
        if s>63:raise RuntimeError('varint overflow')

def build_bounded_models(vals,ctx,cut):
    vals=np.asarray(vals,np.int32);ctx=np.asarray(ctx,np.int32);esc=cut+1;models={};diag=[];entropy=0.0
    for c in range(16):
        x=vals[ctx==c]
        if not x.size:continue
        y=np.minimum(x,esc);sy,f=np.unique(y,return_counts=True);sy=sy.astype(np.int32);f=f.astype(np.int64);cum=np.r_[0,np.cumsum(f,dtype=np.int64)];tot=int(cum[-1]);enc={int(s):(int(cum[i]),int(cum[i+1]),tot) for i,s in enumerate(sy.tolist())};models[c]={'syms':sy,'freq':f,'cum':cum,'total':tot,'enc':enc}
        p=f/tot;H=float(-np.sum(p*np.log2(p)));entropy+=tot*H;diag.append({'id':c,'n':tot,'alphabet':int(len(sy)),'escape_count':int(np.sum(x>cut)),'escape_fraction':float(np.mean(x>cut)),'entropy_bps':H})
    return models,entropy,diag

def serialize_bounded_models(ctx,models,cut):
    ctx=np.asarray(ctx,np.int32);A=cut+2;nm=(A+7)//8;out=bytearray()
    for c in range(16):
        total=int(np.sum(ctx==c))
        if not total:continue
        m=models[c];mask=np.zeros(A,np.uint8);mask[m['syms']]=1;out.extend(np.packbits(mask,bitorder='little').tobytes())
        f=m['freq']
        for q in f[:-1].tolist():vput(out,int(q))
    return bytes(out)
def parse_bounded_models(ctx,b,cut):
    ctx=np.asarray(ctx,np.int32);A=cut+2;nm=(A+7)//8;p=0;models={}
    for c in range(16):
        total=int(np.sum(ctx==c))
        if not total:continue
        if p+nm>len(b):raise RuntimeError('short bounded model mask')
        mask=np.unpackbits(np.frombuffer(b[p:p+nm],np.uint8),bitorder='little',count=A).astype(bool);p+=nm;sy=np.flatnonzero(mask).astype(np.int32)
        if not sy.size:raise RuntimeError(('empty bounded model',c))
        f=[];ss=0
        for _ in range(len(sy)-1):
            q,p=vget(b,p)
            if q<=0:raise RuntimeError(('bounded freq',c,q))
            f.append(int(q));ss+=int(q)
        last=total-ss
        if last<=0:raise RuntimeError(('bounded last freq',c,last,total,ss))
        f.append(last);f=np.asarray(f,np.int64);cum=np.r_[0,np.cumsum(f,dtype=np.int64)];models[c]={'syms':sy,'freq':f,'cum':cum,'total':total}
    if p!=len(b):raise RuntimeError(('bounded model trailing',p,len(b)))
    return models

def arithmetic_encode(vals,ctx,models):
    vals=np.asarray(vals,np.int32);ctx=np.asarray(ctx,np.int32);w=BitWriter();low=0;high=FULL-1;pending=0
    def emit(bit):
        nonlocal pending
        w.bit(bit)
        while pending:w.bit(1-bit);pending-=1
    for x,c0 in zip(vals.tolist(),ctx.tolist()):
        c=int(c0);cl,ch,tot=models[c]['enc'][int(x)];rng=high-low+1;high=low+(rng*ch//tot)-1;low=low+(rng*cl//tot)
        if low>high:raise RuntimeError(('bounded arithmetic collapse',x,c))
        while True:
            if high<HALF:emit(0)
            elif low>=HALF:emit(1);low-=HALF;high-=HALF
            elif low>=Q1 and high<Q3:pending+=1;low-=Q1;high-=Q1
            else:break
            low=(low<<1)&(FULL-1);high=((high<<1)&(FULL-1))|1
    pending+=1
    if low<Q1:emit(0)
    else:emit(1)
    return w.finish()
def arithmetic_decode(n,ctx,models,b):
    ctx=np.asarray(ctx,np.int32);r=BitReader(b);low=0;high=FULL-1;code=0
    for _ in range(32):code=((code<<1)|r.bit())&(FULL-1)
    out=np.empty(n,np.int32)
    for j,c0 in enumerate(ctx.tolist()):
        c=int(c0);m=models[c];tot=int(m['total']);rng=high-low+1;scaled=((code-low+1)*tot-1)//rng;cum=m['cum'];i=bisect.bisect_right(cum.tolist(),int(scaled))-1
        if i<0 or i>=len(m['syms']):raise RuntimeError(('bounded decode symbol',j,c,scaled))
        cl=int(cum[i]);ch=int(cum[i+1]);out[j]=int(m['syms'][i]);high=low+(rng*ch//tot)-1;low=low+(rng*cl//tot)
        while True:
            if high<HALF:pass
            elif low>=HALF:low-=HALF;high-=HALF;code-=HALF
            elif low>=Q1 and high<Q3:low-=Q1;high-=Q1;code-=Q1
            else:break
            low=(low<<1)&(FULL-1);high=((high<<1)&(FULL-1))|1;code=((code<<1)&(FULL-1))|r.bit()
    return out

def bounded_frames(inter,ictx,cut):
    esc=cut+1;binned=np.minimum(inter,esc).astype(np.int32);tail=(inter[inter>cut]-(cut+1)).astype(np.int32);models,entropy,mdiag=build_bounded_models(inter,ictx,cut);model=serialize_bounded_models(ictx,models,cut);payload,bits=arithmetic_encode(binned,ictx,models);pm=parse_bounded_models(ictx,model,cut);rb=arithmetic_decode(len(inter),ictx,pm,payload)
    if not np.array_equal(rb,binned):raise RuntimeError(('bounded arithmetic self decode',cut))
    tailraw=leb_u(tail);return model,payload,tailraw,{'cut':cut,'model_raw_bytes':len(model),'payload_raw_bytes':len(payload),'tail_raw_bytes':len(tailraw),'arithmetic_bits':bits,'entropy_bytes':entropy/8.0,'tail_count':int(tail.size),'tail_fraction':float(tail.size/max(1,inter.size)),'models':mdiag}

def encode_bounded(K,cut,rep9,cache=None):
    if cache is None:cache=structural_sequences(K)
    sh,dc,rawframes,meta,rc,lens,rcomp,vals,phase,event_first,ictx,mctx,r2,r9,d2,d9=cache;rf=run_first_mask(rc);startg=gather_universal(K,ORDER)[2];inter=(startg[~rf]-2).astype(np.int32);model,payload,tail,bdiag=bounded_frames(inter,ictx,cut)
    specs=[rawframes[0],rawframes[1],model,payload,tail,rawframes[3],rawframes[4],rawframes[5],rawframes[6],rawframes[7],rawframes[8],r9 if rep9 else rawframes[9]];frames=[];methods=[];choices=[]
    for i,r in enumerate(specs):
        best,allrows=best_comp(r);n,m,b=best;frames.append(b);methods.append(m);choices.append({'frame':i,'raw_bytes':len(r),'chosen':METHOD_NAMES[m],'bytes':n,'all':allrows})
    oc=int(ORDER[0]|(ORDER[1]<<2)|(ORDER[2]<<4));h=struct.pack(BA_HDR,BA_MAGIC,1,oc,dc,cut,int(rep9),*K.shape,*methods,*[len(x) for x in frames]);names=['run_counts','first_starts','gap_model','gap_arithmetic','gap_tail','long_support','very_support','long_residual','sign_first','sign_repeat','exception_support','exception_magnitude'];parts={names[i]:len(frames[i]) for i in range(12)};parts.update({'header_bytes':BA_HS,'timing_bytes':sum(len(x) for x in frames[:8]),'value_bytes':sum(len(x) for x in frames[8:]),'cut':cut,'rep_magnitude_rice':bool(rep9),'backend_choices':choices,'bounded_diag':bdiag,'magnitude_rice_diag':d9,**meta});return h+b''.join(frames),parts

def decode_bounded(blob):
    q=struct.unpack(BA_HDR,blob[:BA_HS]);magic,ver,oc,dc,cut,rep9,C,L,S,T,*rest=q
    if magic!=BA_MAGIC or ver!=1 or cut not in CUTS:raise RuntimeError('bounded header')
    methods=rest[:12];lf=rest[12:];p=BA_HS;frames=[]
    for n in lf:frames.append(blob[p:p+n]);p+=n
    if p!=len(blob):raise RuntimeError('bounded main length')
    raw=[decomp_one(frames[i],methods[i]) for i in range(12)];order=tuple((oc>>(2*i))&3 for i in range(3));shape=(C,L,S,T);psh=tuple(shape[i] for i in order)+(T,);ntr=int(np.prod(psh[:-1]));rc=leb_dec(raw[0],ntr);nr=int(rc.sum());rf=run_first_mask(rc);nn=int(np.count_nonzero(rc));firstcomp=first_components(rc,order,psh);firstg=first_restore(raw[1],nn,firstcomp,2)
    long=np.unpackbits(np.frombuffer(raw[5],np.uint8),bitorder='little',count=nr).astype(bool);nl=int(long.sum());very=np.unpackbits(np.frombuffer(raw[6],np.uint8),bitorder='little',count=nl).astype(bool) if nl else np.empty(0,bool);res=leb_dec(raw[7],int(very.sum())) if very.any() else np.empty(0,np.int32);runlens=np.ones(nr,np.int32);li=np.flatnonzero(long);runlens[li]=2
    if very.any():runlens[li[very]]=res+3
    rcomp=run_components(rc,order,psh);ictx=inter_context(rc,runlens,rcomp,CTXMODE);models=parse_bounded_models(ictx,raw[2],cut);binned=arithmetic_decode(nr-nn,ictx,models,raw[3]);nt=int(np.sum(binned==cut+1));tv=leb_dec(raw[4],nt) if nt else np.empty(0,np.int32);inter=binned.astype(np.int32);inter[inter==cut+1]=tv+(cut+1);startg=np.empty(nr,np.int32);startg[rf]=firstg;startg[~rf]=inter+2;rows=reconstruct_positions(rc,startg,runlens,T);counts,phase,event_first=metadata_from_positions(rows);ne=int(counts.sum())
    firstsign=np.unpackbits(np.frombuffer(raw[8],np.uint8),bitorder='little',count=nn).astype(bool);rep_mask=~event_first;rsort=np.unpackbits(np.frombuffer(raw[9],np.uint8),bitorder='little',count=ne-nn).astype(bool);repeat=restore_bits(rsort,phase[rep_mask]);signs=np.empty(ne,bool);k=fk=rk=0
    for c0 in counts.tolist():
        c=int(c0)
        if not c:continue
        s=bool(firstsign[fk]);fk+=1;signs[k]=s;k+=1
        for _ in range(1,c):
            if not repeat[rk]:s=not s
            rk+=1;signs[k]=s;k+=1
    if k!=ne or fk!=nn or rk!=repeat.size:raise RuntimeError('bounded sign accounting')
    esort=np.unpackbits(np.frombuffer(raw[10],np.uint8),bitorder='little',count=ne).astype(bool);exc=restore_bits(esort,phase);nex=int(exc.sum());mctx=phase[exc].astype(np.int32)
    if rep9:mag=rice_decode_context(raw[11],mctx,4)
    else:msort=np.frombuffer(raw[11],dtype=DT[dc],count=nex).astype(np.int32) if nex else np.empty(0,np.int32);mag=restore_vals(msort,mctx) if nex else msort
    ab=np.ones(ne,np.int32);ab[exc]=mag+2;vals=np.where(signs,-ab,ab);tr=np.zeros((ntr,T),np.int32);k=0
    for i,pos in enumerate(rows):
        c=pos.size
        if c:tr[i,pos]=vals[k:k+c];k+=c
    if k!=ne:raise RuntimeError('bounded value accounting')
    P=tr.reshape(psh);inv=np.argsort(order);return np.transpose(P,tuple(inv)+(3,))

def decode_out_blob(bo,Oshape):
    if bo[1]=='gap':
        A=decode(bo[6]).reshape(Oshape);return undelta(A,1) if bo[2] else A
    A=decode_out_sparse(bo[6]);return undelta(A,1) if bo[2] else A

def main(path,frac):
    X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());public_eps=float(frac)*std;internal_eps=public_eps*INTERNAL_SAFETY;step=2*internal_eps;raw=int(X.nbytes);G,tm,outids,geom=geometry_map(X,gx,gy)
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    O=np.rint(X[outids]/step).astype(np.int32);K=delta(G,3);cache=structural_sequences(K);inc=[]
    for r2 in (0,1):
        for r9 in (0,1):
            b,parts=encode_main_candidate(K,r2,r9,cache);R=decode_main_candidate(b)
            if not np.array_equal(R,K):raise RuntimeError('incumbent decode')
            inc.append((len(b),r2,r9,b,parts))
    inc.sort(key=lambda r:r[0]);base=inc[0];bo=best_out(O);RO=decode_out_blob(bo,O.shape)
    if not np.array_equal(RO,O):raise RuntimeError('bounded outlier decode')
    base_container=TOP_HS+base[0]+bo[0];rows=[]
    for cut in CUTS:
        for rep9 in (0,1):
            mb,parts=encode_bounded(K,cut,rep9,cache);RK=decode_bounded(mb)
            if not np.array_equal(RK,K):raise RuntimeError(('bounded exact K',cut,rep9))
            container=TOP_HS+len(mb)+bo[0];rows.append((container,cut,rep9,mb,parts))
    rows.sort(key=lambda r:r[0]);w=rows[0];RK=decode_bounded(w[3]);Q=np.cumsum(RK,axis=3,dtype=np.int64).astype(np.int32);Y=np.empty_like(X)
    for tid,c,l,s in tm:Y[tid]=Q[c,l,s].astype(np.float32)*np.float32(step)
    Y[outids]=RO.astype(np.float32)*np.float32(step);me=float(np.max(np.abs(X-Y)));szb,sze=sz3_bytes(X,public_eps)
    out={'file':os.path.basename(path),'shape':list(X.shape),'epsilon_fraction_of_std':float(frac),'public_eps':public_eps,'internal_eps':internal_eps,'raw_bytes':raw,'geometry':geom,'incumbent':{'container_bytes':int(base_container),'main_bytes':base[0],'inter_rice':bool(base[1]),'magnitude_rice':bool(base[2]),'parts':base[4]},'best':{'container_bytes':int(w[0]),'main_bytes':len(w[3]),'cut':int(w[1]),'magnitude_rice':bool(w[2]),'parts':w[4]},'all':[{'container_bytes':int(r[0]),'cut':int(r[1]),'magnitude_rice':bool(r[2]),'parts':r[4]} for r in rows],'improvement_vs_incumbent':float(base_container/w[0]),'sz3':{'bytes':int(szb),'ratio':float(raw/szb),'maxerr':float(sze)},'gain_vs_direct_sz3':float(szb/w[0]),'maxerr':me,'valid':bool(me<=public_eps)}
    if not out['valid']:raise RuntimeError(('bounded hard error',me,public_eps))
    print(json.dumps({'frac':frac,'incumbent':base_container,'best_bytes':w[0],'cut':w[1],'magnitude_rice':bool(w[2]),'improvement':out['improvement_vs_incumbent'],'gain_sz3':out['gain_vs_direct_sz3'],'model':w[4]['gap_model'],'arith':w[4]['gap_arithmetic'],'tail':w[4]['gap_tail'],'maxerr':me},indent=2),flush=True);json.dump(out,open('soda_tight_bounded_arithmetic.json','w'),indent=2)

main(sys.argv[1],float(sys.argv[2]))
