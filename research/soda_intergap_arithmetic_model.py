import bisect,json,math,os,struct,sys
import numpy as np

# Reuse PR #167's audited geometry, run grammar, value semantics, backend
# dictionary and exact outlier codec.  Only the inter-run gap frame changes.
src=open('research/soda_intergap_context_refine.py').read().split('\ndef main(path):')[0]
exec(compile(src,'soda_intergap_context_refine.py','exec'),globals())

AMAG=b'ARIGAP01'
AHDR='<8sBBBB4I11B11Q'
AHS=struct.calcsize(AHDR)
FULL=1<<32;HALF=1<<31;Q1=1<<30;Q3=3<<30

class BitWriter:
    def __init__(self):self.buf=bytearray();self.acc=0;self.n=0;self.bits=0
    def bit(self,b):
        self.acc|=(int(b)&1)<<self.n;self.n+=1;self.bits+=1
        if self.n==8:self.buf.append(self.acc);self.acc=0;self.n=0
    def finish(self):
        if self.n:self.buf.append(self.acc);self.acc=0;self.n=0
        return bytes(self.buf),int(self.bits)

class BitReader:
    def __init__(self,b):self.b=memoryview(b);self.i=0;self.acc=0;self.n=0;self.bits=0
    def bit(self):
        if not self.n:
            if self.i>=len(self.b):self.bits+=1;return 0
            self.acc=int(self.b[self.i]);self.i+=1;self.n=8
        v=self.acc&1;self.acc>>=1;self.n-=1;self.bits+=1;return v


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


def labels_for_kind(rc,lens,rcomp,kind):
    if kind<0:return np.zeros(int(np.maximum(np.asarray(rc,np.int64)-1,0).sum()),np.int32)
    return refined_context(rc,lens,rcomp,int(kind))


def build_models(ctx,vals):
    ctx=np.asarray(ctx,np.int32);vals=np.asarray(vals,np.int32)
    if len(ctx)!=len(vals):raise RuntimeError('model label size')
    models={};entropy=0.0;diag=[]
    for c0 in np.unique(ctx).tolist():
        c=int(c0);x=vals[ctx==c];sy,f=np.unique(x,return_counts=True);sy=sy.astype(np.int32);f=f.astype(np.int64);cum=np.r_[0,np.cumsum(f,dtype=np.int64)];tot=int(cum[-1])
        if tot!=len(x) or np.any(f<=0):raise RuntimeError('model counts')
        mp={int(s):(int(cum[i]),int(cum[i+1]),tot) for i,s in enumerate(sy.tolist())}
        models[c]={'syms':sy,'freq':f,'cum':cum,'total':tot,'enc':mp}
        H=float(-np.sum((f/tot)*np.log2(f/tot))) if tot else 0.0;entropy+=tot*H
        diag.append({'id':c,'n':tot,'alphabet':int(len(sy)),'entropy_bits_per_symbol':H,'entropy_bytes':tot*H/8.0,'min':int(sy[0]),'max':int(sy[-1])})
    return models,entropy,diag


def serialize_models(ctx,models):
    # Decoder already knows which context IDs occur and each context population.
    # Therefore context IDs, totals, and the final frequency are implicit.
    out=bytearray();used=sorted(int(x) for x in np.unique(ctx).tolist())
    for c in used:
        m=models[c];sy=m['syms'];f=m['freq'];vput(out,len(sy));prev=-1
        for s in sy.tolist():
            # Nonnegative sorted gap symbols; code missing integers as delta-1.
            d=int(s) if prev<0 else int(s)-prev-1
            if d<0:raise RuntimeError(('symbol order',c,s,prev));vput(out,d);prev=int(s)
        for q in f[:-1].tolist():vput(out,int(q))
    return bytes(out)


def parse_models(ctx,b):
    ctx=np.asarray(ctx,np.int32);used=sorted(int(x) for x in np.unique(ctx).tolist());p=0;models={}
    for c in used:
        total=int(np.sum(ctx==c));m,p=vget(b,p)
        if m<=0:raise RuntimeError(('empty model',c,m))
        sy=[];prev=-1
        for _ in range(m):
            d,p=vget(b,p);s=int(d) if prev<0 else prev+1+int(d);sy.append(s);prev=s
        f=[];ss=0
        for _ in range(m-1):
            q,p=vget(b,p)
            if q<=0:raise RuntimeError(('bad freq',c,q));f.append(int(q));ss+=int(q)
        last=total-ss
        if last<=0:raise RuntimeError(('bad final freq',c,last,total,ss));f.append(last)
        sy=np.asarray(sy,np.int32);f=np.asarray(f,np.int64);cum=np.r_[0,np.cumsum(f,dtype=np.int64)]
        if int(cum[-1])!=total:raise RuntimeError('model total')
        models[c]={'syms':sy,'freq':f,'cum':cum,'total':total}
    if p!=len(b):raise RuntimeError(('model trailing bytes',p,len(b)))
    return models


def arithmetic_encode(vals,ctx,models):
    vals=np.asarray(vals,np.int32);ctx=np.asarray(ctx,np.int32);w=BitWriter();low=0;high=FULL-1;pending=0
    def emit(bit):
        nonlocal pending
        w.bit(bit)
        while pending:w.bit(1-bit);pending-=1
    for x,c0 in zip(vals.tolist(),ctx.tolist()):
        c=int(c0);cl,ch,tot=models[c]['enc'][int(x)];rng=high-low+1;high=low+(rng*ch//tot)-1;low=low+(rng*cl//tot)
        if low>high:raise RuntimeError(('arith collapsed',x,c,cl,ch,tot,rng))
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
    ctx=np.asarray(ctx,np.int32)
    if len(ctx)!=n:raise RuntimeError(('decode label count',len(ctx),n))
    r=BitReader(b);low=0;high=FULL-1;code=0
    for _ in range(32):code=((code<<1)|r.bit())&(FULL-1)
    out=np.empty(n,np.int32)
    for j,c0 in enumerate(ctx.tolist()):
        c=int(c0);m=models[c];tot=int(m['total']);rng=high-low+1;scaled=((code-low+1)*tot-1)//rng
        cum=m['cum'];i=bisect.bisect_right(cum.tolist(),int(scaled))-1
        if i<0 or i>=len(m['syms']):raise RuntimeError(('arith symbol search',j,c,scaled,tot,i))
        cl=int(cum[i]);ch=int(cum[i+1]);out[j]=int(m['syms'][i]);high=low+(rng*ch//tot)-1;low=low+(rng*cl//tot)
        while True:
            if high<HALF:pass
            elif low>=HALF:low-=HALF;high-=HALF;code-=HALF
            elif low>=Q1 and high<Q3:low-=Q1;high-=Q1;code-=Q1
            else:break
            low=(low<<1)&(FULL-1);high=((high<<1)&(FULL-1))|1;code=((code<<1)&(FULL-1))|r.bit()
    return out


def encode_arith(K,kind,order,cache,common):
    sh,dc,raw,meta,rc,lens,rcomp,inter=cache;ctx=labels_for_kind(rc,lens,rcomp,kind);models,entropy,mdiag=build_models(ctx,inter);model_raw=serialize_models(ctx,models);payload_raw,pbits=arithmetic_encode(inter,ctx,models)
    # Prove the standalone probability representation before container assembly.
    pm=parse_models(ctx,model_raw);rr=arithmetic_decode(len(inter),ctx,pm,payload_raw)
    if not np.array_equal(rr,inter):raise RuntimeError(('arithmetic self decode',kind,int(np.sum(rr!=inter))))
    bm,am=best_comp(model_raw),best_comp(payload_raw);model_best,model_all=bm;payload_best,payload_all=am
    methods=[];frames=[];choices=[]
    # New 11-frame layout: common 0,1; transmitted model; arithmetic payload; then original common 3..9.
    specs=[]
    for old in (0,1):
        n,m,b,allrows,rawlen=common[old];specs.append((n,m,b,allrows,rawlen))
    for rawx,bestx,allx in ((model_raw,model_best,model_all),(payload_raw,payload_best,payload_all)):
        n,m,b=bestx;specs.append((n,m,b,allx,len(rawx)))
    for old in range(3,10):
        n,m,b,allrows,rawlen=common[old];specs.append((n,m,b,allrows,rawlen))
    for i,(n,m,b,allrows,rawlen) in enumerate(specs):methods.append(m);frames.append(b);choices.append({'frame':i,'raw_bytes':rawlen,'chosen':METHOD_NAMES[m],'bytes':n,'all':allrows})
    code=0 if kind<0 else kind+1;oc=int(order[0]|(order[1]<<2)|(order[2]<<4));h=struct.pack(AHDR,AMAG,1,oc,dc,code,*K.shape,*methods,*[len(x) for x in frames]);names=['run_counts','first_starts','gap_model','gap_arithmetic','long_support','very_support','long_residual','sign_first','sign_repeat','exception_support','exception_magnitude'];parts={names[i]:len(frames[i]) for i in range(11)};parts['timing_bytes']=sum(len(x) for x in frames[:7]);parts['value_bytes']=sum(len(x) for x in frames[7:]);parts['header_bytes']=AHS;parts['backend_choices']=choices;parts['context_kind']=kind;parts['context_name']='global' if kind<0 else context_name(kind);parts['entropy_bits']=entropy;parts['entropy_bytes']=entropy/8.0;parts['arithmetic_bits']=pbits;parts['arithmetic_raw_bytes']=len(payload_raw);parts['model_raw_bytes']=len(model_raw);parts['model_diag']=mdiag;parts.update(meta)
    return h+b''.join(frames),parts


def decode_arith(blob):
    q=struct.unpack(AHDR,blob[:AHS]);magic,ver,oc,dc,code,C,L,S,T,*rest=q
    if magic!=AMAG or ver!=1 or code>10:raise RuntimeError(('arith header',magic,ver,code))
    kind=-1 if code==0 else int(code)-1;methods=rest[:11];lf=rest[11:];p=AHS;frames=[]
    for n in lf:frames.append(blob[p:p+n]);p+=n
    if p!=len(blob):raise RuntimeError('arith stream length')
    raw=[decomp_one(frames[i],methods[i]) for i in range(11)];order=tuple((oc>>(2*i))&3 for i in range(3));shape=(C,L,S,T);psh=tuple(shape[i] for i in order)+(T,);ntr=int(np.prod(psh[:-1]));rc=leb_dec(raw[0],ntr);nr=int(rc.sum());rf=run_first_mask(rc);nn=int(np.count_nonzero(rc));firstcomp=first_components(rc,order,psh);firstg=first_restore(raw[1],nn,firstcomp,2)
    long=np.unpackbits(np.frombuffer(raw[4],np.uint8),bitorder='little',count=nr).astype(bool);nl=int(long.sum());very=np.unpackbits(np.frombuffer(raw[5],np.uint8),bitorder='little',count=nl).astype(bool) if nl else np.empty(0,bool);res=leb_dec(raw[6],int(very.sum())) if very.any() else np.empty(0,np.int32);runlens=np.ones(nr,np.int32);li=np.flatnonzero(long);runlens[li]=2
    if very.any():runlens[li[very]]=res+3
    rcomp=run_components(rc,order,psh);ctx=labels_for_kind(rc,runlens,rcomp,kind);models=parse_models(ctx,raw[2]);inter=arithmetic_decode(nr-nn,ctx,models,raw[3]);startg=np.empty(nr,np.int32);startg[rf]=firstg;startg[~rf]=inter+2;rows=reconstruct_positions(rc,startg,runlens,T);counts,phase,event_first=metadata_from_positions(rows);ne=int(counts.sum())
    firstsign=np.unpackbits(np.frombuffer(raw[7],np.uint8),bitorder='little',count=nn).astype(bool);rep_mask=~event_first;rsort=np.unpackbits(np.frombuffer(raw[8],np.uint8),bitorder='little',count=ne-nn).astype(bool);repeat=restore_bits(rsort,phase[rep_mask]);signs=np.empty(ne,bool);k=fk=rk=0
    for c0 in counts.tolist():
        c=int(c0)
        if not c:continue
        sg=bool(firstsign[fk]);fk+=1;signs[k]=sg;k+=1
        for _ in range(1,c):
            if not repeat[rk]:sg=not sg
            rk+=1;signs[k]=sg;k+=1
    if k!=ne or fk!=nn or rk!=repeat.size:raise RuntimeError('arith sign accounting')
    esort=np.unpackbits(np.frombuffer(raw[9],np.uint8),bitorder='little',count=ne).astype(bool);exc=restore_bits(esort,phase);nex=int(exc.sum());msort=np.frombuffer(raw[10],dtype=DT[dc],count=nex).astype(np.int32) if nex else np.empty(0,np.int32);mag=restore_vals(msort,phase[exc]) if nex else msort;ab=np.ones(ne,np.int32);ab[exc]=mag+2;vals=np.where(signs,-ab,ab);tr=np.zeros((ntr,T),np.int32);k=0
    for i,pos in enumerate(rows):
        c=pos.size
        if c:tr[i,pos]=vals[k:k+c];k+=c
    if k!=ne:raise RuntimeError('arith value accounting')
    P=tr.reshape(psh);inv=np.argsort(order);return np.transpose(P,tuple(inv)+(3,))


def main(path):
    order=(0,1,2);X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());eps=.1*std;step=2*eps;rawbytes=X.nbytes;G,tm,outids,geom=geometry_map(X,gx,gy)
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    O=np.rint(X[outids]/step).astype(np.int32);K=delta(G,3);cache=prepare_common(K,order);common=compress_common(cache[2]);bb,bparts=encode_kind(K,3,order,cache,common);BR=decode_kind(bb)
    if not np.array_equal(BR,K):raise RuntimeError('PR167 baseline decode')
    rows=[{'kind':99,'name':'PR167-singleton-relative-rank','main_bytes':len(bb),'parts':bparts,'blob':bb,'decoder':'baseline'}]
    for kind in (-1,0,1,2,3,4,5,6,7,8,9):
        print('ARITH CONTEXT',kind,'global' if kind<0 else context_name(kind),flush=True);b,parts=encode_arith(K,kind,order,cache,common);R=decode_arith(b)
        if not np.array_equal(R,K):raise RuntimeError(('arith exact K',kind))
        rows.append({'kind':kind,'name':parts['context_name'],'main_bytes':len(b),'parts':parts,'blob':b,'decoder':'arith'});print(json.dumps({'kind':kind,'name':parts['context_name'],'main_bytes':len(b),'model_bytes':parts['gap_model'],'payload_bytes':parts['gap_arithmetic'],'entropy_bytes':parts['entropy_bytes'],'arithmetic_raw_bytes':parts['arithmetic_raw_bytes'],'timing_bytes':parts['timing_bytes']},indent=2),flush=True)
    rows.sort(key=lambda x:x['main_bytes']);best=rows[0];RK=decode_kind(best['blob']) if best['decoder']=='baseline' else decode_arith(best['blob']);bo=best_out(O);RO=decode_out_best(bo,O.shape)
    if not np.array_equal(RO,O):raise RuntimeError('arith outlier decode')
    RG=undelta(RK,3);recon=np.empty_like(X)
    for tid,c,l,s in tm:recon[tid]=RG[c,l,s].astype(np.float32)*np.float32(step)
    recon[outids]=RO.astype(np.float32)*np.float32(step);me=float(np.max(np.abs(X-recon)));szb,sze=sz3_bytes(X,eps);container=TOPS+best['main_bytes']+int(bo[0]);baseline=133226
    out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':rawbytes,'eps':eps,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'best':{k:v for k,v in best.items() if k!='blob'},'candidates':[{k:v for k,v in r.items() if k!='blob'} for r in rows],'outlier_bytes':int(bo[0]),'top_header_bytes':TOPS,'container_bytes':container,'ratio':float(rawbytes/container),'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'sz3':{'bytes':int(szb),'ratio':float(rawbytes/szb),'maxerr':float(sze)},'gain_vs_direct_sz3':float(szb/container),'strongest_verified_p75_baseline_bytes':baseline,'gain_vs_strongest_verified_p75_baseline':float(baseline/container),'prior_pr167_bytes':63657,'improvement_vs_pr167_bytes':int(63657-container)}
    print(json.dumps({k:out[k] for k in ('container_bytes','ratio','gain_vs_direct_sz3','gain_vs_strongest_verified_p75_baseline','improvement_vs_pr167_bytes','maxerr','valid')},indent=2),flush=True);json.dump(out,open('soda_intergap_arithmetic_model.json','w'),indent=2)

main(sys.argv[1])
