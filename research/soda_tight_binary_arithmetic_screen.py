import json,os,sys
import numpy as np

src=open('research/soda_tight_refined_context_phase.py').read().rsplit('\nmain(sys.argv[1],float(sys.argv[2]))',1)[0]
exec(compile(src,'soda_tight_refined_context_phase.py','exec'),globals())

FULL=1<<32;HALF=1<<31;Q1=1<<30;Q3=3<<30
class BW:
    def __init__(self):self.b=bytearray();self.a=0;self.n=0
    def put(self,x):
        self.a|=(int(x)&1)<<self.n;self.n+=1
        if self.n==8:self.b.append(self.a);self.a=0;self.n=0
    def finish(self):
        if self.n:self.b.append(self.a)
        return bytes(self.b)
class BR:
    def __init__(self,b):self.b=memoryview(b);self.i=0;self.a=0;self.n=0
    def get(self):
        if not self.n:
            if self.i>=len(self.b):return 0
            self.a=int(self.b[self.i]);self.i+=1;self.n=8
        x=self.a&1;self.a>>=1;self.n-=1;return x

def vput(out,x):
    x=int(x)
    while x>=128:out.append((x&127)|128);x>>=7
    out.append(x)
def vget(b,p):
    x=0;s=0
    while True:
        if p>=len(b):raise RuntimeError('varint EOF')
        q=int(b[p]);p+=1;x|=(q&127)<<s
        if q<128:return x,p
        s+=7

def counts(bits,ctx,nctx):
    bits=np.asarray(bits,bool);ctx=np.asarray(ctx,np.int32);pop=np.bincount(ctx,minlength=nctx).astype(np.int64);one=np.bincount(ctx,weights=bits.astype(np.int64),minlength=nctx).astype(np.int64);return pop,one

def model_bytes(one):
    out=bytearray()
    for x in np.asarray(one).tolist():vput(out,int(x))
    return bytes(out)
def parse_ones(b,nctx):
    p=0;o=np.empty(nctx,np.int64)
    for i in range(nctx):o[i],p=vget(b,p)
    return o,p

def arith_encode(bits,ctx,pop,one):
    bits=np.asarray(bits,bool);ctx=np.asarray(ctx,np.int32);w=BW();low=0;high=FULL-1;pending=0
    def emit(x):
        nonlocal pending
        w.put(x)
        while pending:w.put(1-x);pending-=1
    for bit,c0 in zip(bits.tolist(),ctx.tolist()):
        c=int(c0);n=int(pop[c]);n1=int(one[c]);n0=n-n1
        if n0==0:
            if not bit:raise RuntimeError('deterministic one model')
            continue
        if n1==0:
            if bit:raise RuntimeError('deterministic zero model')
            continue
        rng=high-low+1
        if bit:
            high=low+(rng*n//n)-1;low=low+(rng*n0//n)
        else:high=low+(rng*n0//n)-1
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
def arith_decode(ctx,pop,one,payload):
    ctx=np.asarray(ctx,np.int32);r=BR(payload);low=0;high=FULL-1;code=0
    for _ in range(32):code=((code<<1)|r.get())&(FULL-1)
    out=np.empty(len(ctx),bool)
    for j,c0 in enumerate(ctx.tolist()):
        c=int(c0);n=int(pop[c]);n1=int(one[c]);n0=n-n1
        if n0==0:out[j]=True;continue
        if n1==0:out[j]=False;continue
        rng=high-low+1;cut=low+(rng*n0//n)
        if code<cut:out[j]=False;high=cut-1
        else:out[j]=True;low=cut
        while True:
            if high<HALF:pass
            elif low>=HALF:low-=HALF;high-=HALF;code-=HALF
            elif low>=Q1 and high<Q3:low-=Q1;high-=Q1;code-=Q1
            else:break
            low=(low<<1)&(FULL-1);high=((high<<1)&(FULL-1))|1;code=((code<<1)&(FULL-1))|r.get()
    return out

def frame(bits,ctx,nctx):
    pop,one=counts(bits,ctx,nctx);m=model_bytes(one);p=arith_encode(bits,ctx,pop,one);raw=m+p;best=compress_exact(raw);de=decomp_one(best[2],best[1]);oo,q=parse_ones(de,nctx);pp=de[q:]
    if not np.array_equal(oo,one):raise RuntimeError('binary model roundtrip')
    R=arith_decode(ctx,pop,oo,pp)
    if not np.array_equal(R,np.asarray(bits,bool)):raise RuntimeError('binary arithmetic exact decode')
    H=0.0
    for n,o in zip(pop.tolist(),one.tolist()):
        if n and o not in (0,n):
            p1=o/n;H+=-o*np.log2(p1)-(n-o)*np.log2(1-p1)
    return {'bytes':int(best[0]),'raw_frame_bytes':len(raw),'model_bytes':len(m),'arithmetic_bytes':len(p),'backend':METHOD_NAMES[int(best[1])],'conditional_entropy_bytes':H/8.0,'contexts':nctx,'ones':int(np.sum(bits)),'n':len(bits)}

def event_meta(K):
    P=np.transpose(K,ORDER+(3,));sh=P.shape;tr=P.reshape(-1,sh[-1]);comp=[];counts=[]
    ca=ORDER.index(0)
    for i,row in enumerate(tr):
        n=int(np.count_nonzero(row));counts.append(n)
        if n:
            cc=int(np.unravel_index(i,sh[:-1])[ca]);comp.extend([cc]*n)
    return np.asarray(comp,np.uint8),np.asarray(counts,np.int32)

def bitplanes(K):
    sh,rc,startg,lens,rcomp,vals,phase,event_first,diag=gather_universal(K,ORDER);comp,tc=event_meta(K);ne=len(vals)
    if len(comp)!=ne:raise RuntimeError(('event component count',len(comp),ne))
    signs=vals<0;prev=np.empty(ne,bool);k=0
    for n0 in tc.tolist():
        n=int(n0)
        if not n:continue
        prev[k]=signs[k]
        if n>1:prev[k+1:k+n]=signs[k:k+n-1]
        k+=n
    if k!=ne:raise RuntimeError('previous sign accounting')
    rm=~event_first;repeat=(signs==prev)[rm];rp=phase[rm].astype(np.int32);rcp=comp[rm].astype(np.int32);inside=(rp!=0).astype(np.int32)
    signctx=[('none',np.zeros(len(repeat),np.int32),1),('phase',rp,4),('component',rcp,3),('component-x-phase',rcp*4+rp,12),('component-x-inside',rcp*2+inside,6)]
    exc=np.abs(vals)!=1;ph=phase.astype(np.int32);cp=comp.astype(np.int32);sg=signs.astype(np.int32);ins=(ph!=0).astype(np.int32)
    excctx=[('none',np.zeros(ne,np.int32),1),('phase',ph,4),('component',cp,3),('component-x-phase',cp*4+ph,12),('phase-x-sign',ph*2+sg,8),('component-x-phase-x-sign',(cp*4+ph)*2+sg,24),('component-x-inside-x-sign',(cp*2+ins)*2+sg,12)]
    return repeat,signctx,exc,excctx

def screen(K,current_container,parts):
    repeat,sc,exc,ec=bitplanes(K);sr=[];er=[]
    for name,c,n in sc:
        d=frame(repeat,c,n);d['name']=name;sr.append(d)
    for name,c,n in ec:
        d=frame(exc,c,n);d['name']=name;er.append(d)
    sr.sort(key=lambda x:x['bytes']);er.sort(key=lambda x:x['bytes']);old=int(parts['sign_repeat']+parts['exception_support']);new=int(sr[0]['bytes']+er[0]['bytes']+2);pred=int(current_container-old+new)
    return {'old_binary_bytes':old,'old_sign_repeat_bytes':int(parts['sign_repeat']),'old_exception_support_bytes':int(parts['exception_support']),'best_sign':sr[0],'best_exception':er[0],'all_sign':sr,'all_exception':er,'new_binary_bytes_including_2_mode_bytes':new,'predicted_container_bytes':pred,'saving':int(current_container-pred)}

def main(path,frac):
    frac=float(frac);X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());public_eps=frac*std;internal_eps=public_eps*INTERNAL_SAFETY;step=2*internal_eps;G0,tm,outids,geom=geometry_map(X,gx,gy);arms=[]
    G,O=nearest_states(X,tm,outids,G0.shape,step);K=delta(G,3);mb,parts=prepare_refined_main(K);bo=best_out(O);cur=TOP_HS+len(mb)+int(bo[0]);arms.append({'state':'nearest','current_bytes':cur,'screen':screen(K,cur,parts)})
    G,P,O,OP,pdiag=phase_quantize(X,tm,outids,G0.shape,step);K=delta(G,3);mb,parts=prepare_refined_main(K);bo=best_out(O);top,pacct=encode_phase_top(internal_eps,P,OP,mb,bo);cur=len(top);arms.append({'state':'phase16','current_bytes':cur,'screen':screen(K,cur,parts)})
    szb,sze=sz3_bytes(X,public_eps);rows=[]
    for a in arms:
        p=a['screen']['predicted_container_bytes'];rows.append({'state':a['state'],'current_bytes':a['current_bytes'],'predicted_bytes':p,'saving':a['screen']['saving'],'gain_vs_direct_sz3':float(szb/p),'clears_2x':bool(p<=szb/2),'screen':a['screen']})
    rows.sort(key=lambda r:r['predicted_bytes']);b=rows[0];out={'file':os.path.basename(path),'shape':list(X.shape),'epsilon_fraction_of_std':frac,'public_eps':public_eps,'internal_eps':internal_eps,'geometry':geom,'sz3':{'bytes':int(szb),'maxerr':float(sze)},'strict_two_x_target_bytes':szb/2,'best':b,'arms':rows}
    print(json.dumps({'frac':frac,'target':out['strict_two_x_target_bytes'],'state':b['state'],'current':b['current_bytes'],'old_binary':b['screen']['old_binary_bytes'],'best_sign':b['screen']['best_sign']['name'],'sign_bytes':b['screen']['best_sign']['bytes'],'best_exc':b['screen']['best_exception']['name'],'exc_bytes':b['screen']['best_exception']['bytes'],'predicted':b['predicted_bytes'],'saving':b['saving'],'gain':b['gain_vs_direct_sz3'],'clears_2x':b['clears_2x']},indent=2),flush=True);json.dump(out,open('soda_tight_binary_arithmetic_screen.json','w'),indent=2)
main(sys.argv[1],sys.argv[2])
