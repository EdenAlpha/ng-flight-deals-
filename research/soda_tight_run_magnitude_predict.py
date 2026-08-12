import json,os,struct,sys
import numpy as np

# Reuse PR #176's exact tight-fidelity codec machinery and backend menu.
src=open('research/soda_tight_rice_frames.py').read().split('\ndef main(path,frac):')[0]
exec(compile(src,'soda_tight_rice_frames.py','exec'),globals())

MAGIC=b'RMPRED01'
HDR='<8sBBBB4I10B10Q'
HS=struct.calcsize(HDR)
TMAG=b'RMTOP001'; THDR='<8sdBBQQ'; THS=struct.calcsize(THDR)


def zz(x):
    x=int(x);return 2*x if x>=0 else -2*x-1

def unzz(u):
    u=int(u);return u//2 if (u&1)==0 else -(u//2)-1

def predictor_name(m):
    return {0:'baseline',1:'previous-event-magnitude',2:'previous-exception-magnitude',3:'causal-linear-magnitude'}[m]

def residuals_from_ab(ab,exc,phase,mode):
    ab=np.asarray(ab,np.int32);exc=np.asarray(exc,bool);phase=np.asarray(phase,np.uint8)
    if mode==0:return (ab[exc]-2).astype(np.int32)
    r=[];last_exc=1;run_hist=[]
    for i,a0 in enumerate(ab.tolist()):
        ph=int(phase[i]);a=int(a0)
        if ph in (0,1):
            run_hist=[];last_exc=1
        if mode==1:
            pred=run_hist[-1] if run_hist else 1
        elif mode==2:
            pred=last_exc
        elif mode==3:
            if len(run_hist)>=2:pred=max(1,2*run_hist[-1]-run_hist[-2])
            elif run_hist:pred=run_hist[-1]
            else:pred=1
        else:raise ValueError(mode)
        if exc[i]:
            r.append(a-pred);last_exc=a
        run_hist.append(a)
        if ph in (0,3):
            run_hist=[];last_exc=1
    return np.asarray(r,np.int32)

def reconstruct_ab(exc,phase,residual,mode):
    exc=np.asarray(exc,bool);phase=np.asarray(phase,np.uint8);residual=np.asarray(residual,np.int32)
    ab=np.ones(exc.size,np.int32);k=0;last_exc=1;run_hist=[]
    for i in range(exc.size):
        ph=int(phase[i])
        if ph in (0,1):run_hist=[];last_exc=1
        if mode==1:pred=run_hist[-1] if run_hist else 1
        elif mode==2:pred=last_exc
        elif mode==3:
            if len(run_hist)>=2:pred=max(1,2*run_hist[-1]-run_hist[-2])
            elif run_hist:pred=run_hist[-1]
            else:pred=1
        else:raise ValueError(mode)
        if exc[i]:
            a=pred+int(residual[k]);k+=1
            if a<=1:raise RuntimeError(('invalid reconstructed exception magnitude',i,a,pred))
            ab[i]=a;last_exc=a
        run_hist.append(int(ab[i]))
        if ph in (0,3):run_hist=[];last_exc=1
    if k!=residual.size:raise RuntimeError(('residual count',k,residual.size))
    return ab

def encode_residual(res,ctx,rep):
    res=np.asarray(res,np.int32);ctx=np.asarray(ctx,np.int32);sr,_=reorder_vals(res,ctx)
    if rep==1:
        raw=leb_u(np.asarray([zz(x) for x in sr.tolist()],np.int32));diag={'rep':'zigzag-leb128','other_fraction':None}
    elif rep==2:
        code=np.full(sr.size,3,np.uint8);code[sr==0]=0;code[sr==1]=1;code[sr==-1]=2
        bits=np.empty(sr.size*2,np.uint8);bits[0::2]=code&1;bits[1::2]=(code>>1)&1;tb=np.packbits(bits,bitorder='little').tobytes();other=sr[code==3];ob=leb_u(np.asarray([zz(x) for x in other.tolist()],np.int32));raw=struct.pack('<I',len(tb))+tb+ob;diag={'rep':'ternary-residual-plus-other','other_fraction':float(np.mean(code==3)) if code.size else 0.0,'zero_fraction':float(np.mean(code==0)) if code.size else 0.0,'pm1_fraction':float(np.mean((code==1)|(code==2))) if code.size else 0.0}
    else:raise ValueError(rep)
    diag.update({'count':int(sr.size),'mean_abs_residual':float(np.mean(np.abs(sr))) if sr.size else 0.0,'p50_abs_residual':float(np.median(np.abs(sr))) if sr.size else 0.0,'p90_abs_residual':float(np.quantile(np.abs(sr),.9)) if sr.size else 0.0,'raw_bytes':len(raw)})
    return raw,diag

def decode_residual(raw,ctx,rep):
    ctx=np.asarray(ctx,np.int32);n=ctx.size
    if rep==1:
        u=leb_dec(raw,n);sr=np.asarray([unzz(x) for x in u.tolist()],np.int32)
    elif rep==2:
        if len(raw)<4:raise RuntimeError('short residual frame')
        lt=struct.unpack('<I',raw[:4])[0];tb=raw[4:4+lt];rest=raw[4+lt:];bits=np.unpackbits(np.frombuffer(tb,np.uint8),bitorder='little',count=2*n).reshape(n,2);code=(bits[:,0]+2*bits[:,1]).astype(np.uint8);no=int(np.sum(code==3));u=leb_dec(rest,no);oth=np.asarray([unzz(x) for x in u.tolist()],np.int32);sr=np.empty(n,np.int32);sr[code==0]=0;sr[code==1]=1;sr[code==2]=-1;sr[code==3]=oth
    else:raise ValueError(rep)
    return restore_vals(sr,ctx).astype(np.int32)

def prepare(K):
    sh,dc,rawframes,meta=prepare_raw_frames(K,ORDER,CTXMODE);sh2,rc,startg,lens,rcomp,vals,phase,event_first,diag=gather_universal(K,ORDER)
    if tuple(sh)!=tuple(sh2):raise RuntimeError('shape mismatch')
    ab=np.abs(vals).astype(np.int32);exc=ab!=1;mctx=phase[exc].astype(np.int32)
    baseline=(ab[exc]-2).astype(np.int32);sb,_=reorder_vals(baseline,mctx)
    if sb.astype(DT[dc],copy=False).tobytes()!=rawframes[9]:raise RuntimeError('baseline magnitude mismatch')
    return sh,dc,rawframes,meta,rc,lens,rcomp,vals,phase,event_first,ab,exc,mctx

def encode_candidate(K,mode,rep,cache):
    sh,dc,rawframes,meta,rc,lens,rcomp,vals,phase,event_first,ab,exc,mctx=cache
    raws=list(rawframes);diag={'predictor':'baseline','rep':'baseline'}
    if mode!=0:
        r=residuals_from_ab(ab,exc,phase,mode);raw9,diag=encode_residual(r,mctx,rep);r2=decode_residual(raw9,mctx,rep);ab2=reconstruct_ab(exc,phase,r2,mode)
        if not np.array_equal(ab2,ab):raise RuntimeError(('residual magnitude roundtrip',mode,rep))
        raws[9]=raw9
    frames=[];methods=[];choices=[]
    for i,r0 in enumerate(raws):
        best,allrows=best_comp(r0);n,m,b=best;frames.append(b);methods.append(m);choices.append({'frame':i,'raw_bytes':len(r0),'chosen':METHOD_NAMES[m],'bytes':n,'all':allrows})
    oc=int(ORDER[0]|(ORDER[1]<<2)|(ORDER[2]<<4));code=int(mode)|(int(rep)<<3);h=struct.pack(HDR,MAGIC,1,oc,dc,code,*K.shape,*methods,*[len(x) for x in frames]);names=['run_counts','first_starts','inter_starts','long_support','very_support','long_residual','sign_first','sign_repeat','exception_support','exception_magnitude'];parts={names[i]:len(frames[i]) for i in range(10)};parts.update({'header_bytes':HS,'timing_bytes':sum(len(x) for x in frames[:6]),'value_bytes':sum(len(x) for x in frames[6:]),'predictor_mode':mode,'predictor_name':predictor_name(mode),'residual_rep':rep,'residual_diag':diag,'backend_choices':choices,**meta})
    return h+b''.join(frames),parts

def decode_candidate(blob):
    q=struct.unpack(HDR,blob[:HS]);magic,ver,oc,dc,code,C,L,S,T,*rest=q
    if magic!=MAGIC or ver!=1:raise RuntimeError('magnitude predictor header')
    mode=int(code)&7;rep=int(code)>>3;methods=rest[:10];lensf=rest[10:];p=HS;frames=[]
    for n in lensf:frames.append(blob[p:p+n]);p+=n
    if p!=len(blob):raise RuntimeError('magnitude predictor stream length')
    raw=[decomp_one(frames[i],methods[i]) for i in range(10)];order=tuple((oc>>(2*i))&3 for i in range(3));shape=(C,L,S,T);psh=tuple(shape[i] for i in order)+(T,);ntr=int(np.prod(psh[:-1]));rc=leb_dec(raw[0],ntr);nr=int(rc.sum());rf=run_first_mask(rc);nn=int(np.count_nonzero(rc));firstcomp=first_components(rc,order,psh);firstg=first_restore(raw[1],nn,firstcomp,2);long=np.unpackbits(np.frombuffer(raw[3],np.uint8),bitorder='little',count=nr).astype(bool);nl=int(long.sum());very=np.unpackbits(np.frombuffer(raw[4],np.uint8),bitorder='little',count=nl).astype(bool) if nl else np.empty(0,bool);lr=leb_dec(raw[5],int(very.sum())) if very.any() else np.empty(0,np.int32);runlens=np.ones(nr,np.int32);li=np.flatnonzero(long);runlens[li]=2
    if very.any():runlens[li[very]]=lr+3
    rcomp=run_components(rc,order,psh);ictx=inter_context(rc,runlens,rcomp,CTXMODE);ss=leb_dec(raw[2],nr-nn);inter=restore_vals(ss,ictx).astype(np.int32);startg=np.empty(nr,np.int32);startg[rf]=firstg;startg[~rf]=inter+2;rows=reconstruct_positions(rc,startg,runlens,T);counts,phase,event_first=metadata_from_positions(rows);ne=int(counts.sum());firstsign=np.unpackbits(np.frombuffer(raw[6],np.uint8),bitorder='little',count=nn).astype(bool);rep_mask=~event_first;rsort=np.unpackbits(np.frombuffer(raw[7],np.uint8),bitorder='little',count=ne-nn).astype(bool);repeat=restore_bits(rsort,phase[rep_mask]);signs=np.empty(ne,bool);k=fk=rk=0
    for c0 in counts.tolist():
        c=int(c0)
        if not c:continue
        s=bool(firstsign[fk]);fk+=1;signs[k]=s;k+=1
        for _ in range(1,c):
            if not repeat[rk]:s=not s
            rk+=1;signs[k]=s;k+=1
    if k!=ne or fk!=nn or rk!=repeat.size:raise RuntimeError('sign accounting')
    esort=np.unpackbits(np.frombuffer(raw[8],np.uint8),bitorder='little',count=ne).astype(bool);exc=restore_bits(esort,phase);nex=int(exc.sum());mctx=phase[exc].astype(np.int32)
    if mode==0:
        msort=np.frombuffer(raw[9],dtype=DT[dc],count=nex).astype(np.int32) if nex else np.empty(0,np.int32);mag=restore_vals(msort,mctx) if nex else msort;ab=np.ones(ne,np.int32);ab[exc]=mag+2
    else:
        residual=decode_residual(raw[9],mctx,rep);ab=reconstruct_ab(exc,phase,residual,mode)
    vals=np.where(signs,-ab,ab);tr=np.zeros((ntr,T),np.int32);k=0
    for i,pos in enumerate(rows):
        c=pos.size
        if c:tr[i,pos]=vals[k:k+c];k+=c
    if k!=ne:raise RuntimeError('value accounting')
    P=tr.reshape(psh);inv=np.argsort(order);return np.transpose(P,tuple(inv)+(3,))

def decode_outlier(bo,Oshape):
    if bo[1]=='gap':A=decode(bo[6]).reshape(Oshape);return undelta(A,1) if bo[2] else A
    A=decode_out_sparse(bo[6]);return undelta(A,1) if bo[2] else A

def main(path,frac):
    X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());public_eps=float(frac)*std;internal_eps=public_eps*INTERNAL_SAFETY;step=2*internal_eps;rawbytes=int(X.nbytes);G,tm,outids,geom=geometry_map(X,gx,gy)
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    O=np.rint(X[outids]/step).astype(np.int32);K=delta(G,3);bo=best_out(O);RO=decode_outlier(bo,O.shape)
    if not np.array_equal(RO,O):raise RuntimeError('outlier decode')
    cache=prepare(K);rows=[]
    for mode,rep in [(0,0),(1,1),(1,2),(2,1),(2,2),(3,1),(3,2)]:
        print('MAGPRED',mode,predictor_name(mode),'REP',rep,flush=True);mb,parts=encode_candidate(K,mode,rep,cache);RK=decode_candidate(mb)
        if not np.array_equal(RK,K):raise RuntimeError(('exact K',mode,rep))
        rows.append({'mode':mode,'predictor':predictor_name(mode),'rep':rep,'main_bytes':len(mb),'container_bytes':THS+len(mb)+int(bo[0]),'parts':parts,'blob':mb});print(json.dumps({'mode':mode,'predictor':predictor_name(mode),'rep':rep,'container':rows[-1]['container_bytes'],'mag_bytes':parts['exception_magnitude'],'value_bytes':parts['value_bytes'],'diag':parts['residual_diag']},indent=2),flush=True)
    rows.sort(key=lambda r:r['container_bytes']);best=rows[0];RK=decode_candidate(best['blob']);RG=undelta(RK,3);Y=np.empty_like(X)
    for tid,c,l,s in tm:Y[tid]=RG[c,l,s].astype(np.float32)*np.float32(step)
    Y[outids]=RO.astype(np.float32)*np.float32(step);me=float(np.max(np.abs(X-Y)));szb,sze=sz3_bytes(X,public_eps);obb=bo[6];ok=0 if bo[1]=='gap' else 1;td=1 if bo[2] else 0;top=struct.pack(THDR,TMAG,internal_eps,ok,td,len(best['blob']),len(obb))+best['blob']+obb
    out={'file':os.path.basename(path),'shape':list(X.shape),'epsilon_fraction_of_std':float(frac),'public_eps':public_eps,'internal_eps':internal_eps,'raw_bytes':rawbytes,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'best':{k:v for k,v in best.items() if k!='blob'},'candidates':[{k:v for k,v in r.items() if k!='blob'} for r in rows],'outlier_bytes':int(bo[0]),'container_bytes':len(top),'ratio':float(rawbytes/len(top)),'maxerr':me,'valid':bool(me<=public_eps*(1+3e-6)),'sz3':{'bytes':int(szb),'ratio':float(rawbytes/szb),'maxerr':float(sze)},'gain_vs_direct_sz3':float(szb/len(top)),'pr176_best_reference':None}
    if not out['valid']:raise RuntimeError(('hard error',me,public_eps))
    print(json.dumps({k:out[k] for k in ('epsilon_fraction_of_std','container_bytes','ratio','gain_vs_direct_sz3','K_nonzero_fraction','maxerr','valid')},indent=2),flush=True);print(json.dumps(out['best'],indent=2),flush=True);json.dump(out,open('soda_tight_run_magnitude_predict.json','w'),indent=2)

main(sys.argv[1],float(sys.argv[2]))
