import json,os,struct,sys
import numpy as np

# Reuse the audited PR161 structural codec, geometry, outlier dictionary and
# exact backend menu. This experiment changes only two already-defined integer
# frames: inter-run gap-minus-2 and exception magnitude-minus-2.
src=open('research/soda_intergap_backend_hybrid.py').read().split('\ndef main(path):')[0]
exec(compile(src,'soda_intergap_backend_hybrid.py','exec'),globals())

RICE_MAGIC=b'TRICE001'
RICE_HDR='<8sBBBB4I10B10Q'
RICE_HS=struct.calcsize(RICE_HDR)
TOP_MAGIC=b'TRTOP001'
TOP_HDR='<8sdBBQQ'
TOP_HS=struct.calcsize(TOP_HDR)
FROZEN_METHODS=(3,3,3,3,3,3,0,3,3,3)
INTERNAL_SAFETY=1.0-1e-4
CTXMODE=4
ORDER=(0,1,2)


def rice_k(vals):
    vals=np.asarray(vals,np.int64)
    if not vals.size:return 0
    best=None
    for k in range(16):
        bits=int(np.sum(vals>>k))+int(vals.size)*(1+k)
        cand=(bits,k)
        if best is None or cand<best:best=cand
    return int(best[1])


def rice_pack_group(vals,k):
    vals=np.asarray(vals,np.int64)
    if not vals.size:return b'',0
    q=vals>>k;lengths=q+1+k;starts=np.empty(vals.size,np.int64);starts[0]=0
    if vals.size>1:starts[1:]=np.cumsum(lengths[:-1],dtype=np.int64)
    total=int(np.sum(lengths));bits=np.zeros(total,np.uint8);bits[starts+q]=1
    if k:
        rem=vals&((1<<k)-1);base=starts+q+1
        for b in range(k):bits[base+b]=((rem>>b)&1).astype(np.uint8)
    return np.packbits(bits,bitorder='little').tobytes(),total


def rice_unpack_group(payload,bitcount,count,k):
    if count==0:
        if bitcount!=0 or payload:raise RuntimeError('nonempty empty Rice group')
        return np.empty(0,np.int32)
    data=np.frombuffer(payload,np.uint8);out=np.empty(count,np.int32);p=0
    for i in range(count):
        q=0
        while True:
            if p>=bitcount:raise RuntimeError(('Rice unary overrun',i,p,bitcount))
            bit=(int(data[p>>3])>>(p&7))&1;p+=1
            if bit:break
            q+=1
        rem=0
        for b in range(k):
            if p>=bitcount:raise RuntimeError(('Rice remainder overrun',i,p,bitcount))
            rem|=((int(data[p>>3])>>(p&7))&1)<<b;p+=1
        out[i]=(q<<k)|rem
    if p!=bitcount:raise RuntimeError(('Rice trailing bits',p,bitcount))
    return out


def rice_encode_context(vals,ctx,nctx):
    vals=np.asarray(vals,np.int32);ctx=np.asarray(ctx,np.int32)
    if vals.size!=ctx.size:raise RuntimeError('Rice context length')
    if vals.size and (np.min(vals)<0 or np.min(ctx)<0 or np.max(ctx)>=nctx):raise RuntimeError('Rice domain')
    chunks=[];ks=[];bitcounts=[];counts=[];rawbits=0
    for c in range(nctx):
        v=vals[ctx==c];k=rice_k(v);b,nb=rice_pack_group(v,k);ks.append(k);bitcounts.append(nb);counts.append(int(v.size));chunks.append(b);rawbits+=nb
    h=struct.pack('<B',nctx)+bytes(ks)+b''.join(struct.pack('<I',int(x)) for x in bitcounts)
    return h+b''.join(chunks),{'contexts':nctx,'ks':ks,'counts':counts,'rice_bits':int(rawbits),'rice_payload_bytes':sum(len(x) for x in chunks),'rice_frame_bytes':len(h)+sum(len(x) for x in chunks)}


def rice_decode_context(blob,ctx,nctx):
    ctx=np.asarray(ctx,np.int32);p=0
    if len(blob)<1:raise RuntimeError('short Rice frame')
    nc=blob[p];p+=1
    if nc!=nctx:raise RuntimeError(('Rice context count',nc,nctx))
    if len(blob)<p+nctx+4*nctx:raise RuntimeError('short Rice header')
    ks=list(blob[p:p+nctx]);p+=nctx;bitcounts=list(struct.unpack('<'+'I'*nctx,blob[p:p+4*nctx]));p+=4*nctx
    grouped=[]
    for c in range(nctx):
        count=int(np.sum(ctx==c));nb=int(bitcounts[c]);nbyte=(nb+7)//8;payload=blob[p:p+nbyte];p+=nbyte
        if len(payload)!=nbyte:raise RuntimeError('short Rice payload')
        grouped.append(rice_unpack_group(payload,nb,count,int(ks[c])))
    if p!=len(blob):raise RuntimeError(('Rice frame trailing bytes',p,len(blob)))
    sv=np.concatenate(grouped) if grouped else np.empty(0,np.int32)
    if sv.size!=ctx.size:raise RuntimeError(('Rice decoded count',sv.size,ctx.size))
    return restore_vals(sv,ctx).astype(np.int32)


def structural_sequences(K):
    sh,dc,rawframes,meta=prepare_raw_frames(K,ORDER,CTXMODE)
    sh2,rc,startg,lens,rcomp,vals,phase,event_first,diag=gather_universal(K,ORDER)
    if tuple(sh2)!=tuple(sh):raise RuntimeError('shape disagreement')
    rf=run_first_mask(rc);inter=(startg[~rf]-2).astype(np.int32);ictx=inter_context(rc,lens,rcomp,CTXMODE)
    ab=np.abs(vals);exc=ab!=1;mag=(ab[exc]-2).astype(np.int32);mctx=phase[exc].astype(np.int32)
    # Exact audits against the current PR161 raw representations.
    si,_=reorder_vals(inter,ictx)
    if leb_u(si)!=rawframes[2]:raise RuntimeError('inter baseline mismatch')
    sm,_=reorder_vals(mag,mctx)
    if sm.astype(DT[dc],copy=False).tobytes()!=rawframes[9]:raise RuntimeError('magnitude baseline mismatch')
    r2,d2=rice_encode_context(inter,ictx,16);r9,d9=rice_encode_context(mag,mctx,4)
    if not np.array_equal(rice_decode_context(r2,ictx,16),inter):raise RuntimeError('inter Rice roundtrip')
    if not np.array_equal(rice_decode_context(r9,mctx,4),mag):raise RuntimeError('magnitude Rice roundtrip')
    return sh,dc,rawframes,meta,rc,lens,rcomp,vals,phase,event_first,ictx,mctx,r2,r9,d2,d9


def compress_frames(rawframes,rep2,rep9,r2,r9):
    frames=[];methods=[];choices=[]
    for i,raw0 in enumerate(rawframes):
        raw=r2 if (i==2 and rep2) else (r9 if (i==9 and rep9) else raw0)
        best,allrows=best_comp(raw);n,m,b=best;frames.append(b);methods.append(m);choices.append({'frame':i,'raw_bytes':len(raw),'chosen':METHOD_NAMES[m],'bytes':n,'all':allrows})
    return frames,methods,choices


def encode_main_candidate(K,rep2,rep9,cache=None):
    if cache is None:cache=structural_sequences(K)
    sh,dc,rawframes,meta,rc,lens,rcomp,vals,phase,event_first,ictx,mctx,r2,r9,d2,d9=cache
    frames,methods,choices=compress_frames(rawframes,rep2,rep9,r2,r9);oc=int(ORDER[0]|(ORDER[1]<<2)|(ORDER[2]<<4));code=int(rep2)|(int(rep9)<<1)
    h=struct.pack(RICE_HDR,RICE_MAGIC,1,oc,dc,code,*K.shape,*methods,*[len(x) for x in frames])
    names=['run_counts','first_starts','inter_starts','long_support','very_support','long_residual','sign_first','sign_repeat','exception_support','exception_magnitude'];parts={names[i]:len(frames[i]) for i in range(10)};parts.update({'header_bytes':RICE_HS,'timing_bytes':sum(len(x) for x in frames[:6]),'value_bytes':sum(len(x) for x in frames[6:]),'rep_inter_rice':bool(rep2),'rep_magnitude_rice':bool(rep9),'backend_choices':choices,'inter_rice_diag':d2,'magnitude_rice_diag':d9,**meta})
    return h+b''.join(frames),parts


def decode_main_candidate(blob):
    q=struct.unpack(RICE_HDR,blob[:RICE_HS]);magic,ver,oc,dc,code,C,L,S,T,*rest=q
    if magic!=RICE_MAGIC or ver!=1:raise RuntimeError('Rice main header')
    rep2=bool(code&1);rep9=bool(code&2);methods=rest[:10];lensf=rest[10:];p=RICE_HS;frames=[]
    for n in lensf:frames.append(blob[p:p+n]);p+=n
    if p!=len(blob):raise RuntimeError('Rice main stream length')
    raw=[decomp_one(frames[i],methods[i]) for i in range(10)];order=tuple((oc>>(2*i))&3 for i in range(3));shape=(C,L,S,T);psh=tuple(shape[i] for i in order)+(T,);ntr=int(np.prod(psh[:-1]));rc=leb_dec(raw[0],ntr);nr=int(rc.sum());rf=run_first_mask(rc);nn=int(np.count_nonzero(rc));firstcomp=first_components(rc,order,psh);firstg=first_restore(raw[1],nn,firstcomp,2)
    long=np.unpackbits(np.frombuffer(raw[3],np.uint8),bitorder='little',count=nr).astype(bool);nl=int(long.sum());very=np.unpackbits(np.frombuffer(raw[4],np.uint8),bitorder='little',count=nl).astype(bool) if nl else np.empty(0,bool);res=leb_dec(raw[5],int(very.sum())) if very.any() else np.empty(0,np.int32);runlens=np.ones(nr,np.int32);li=np.flatnonzero(long);runlens[li]=2
    if very.any():runlens[li[very]]=res+3
    rcomp=run_components(rc,order,psh);ictx=inter_context(rc,runlens,rcomp,CTXMODE)
    if rep2:inter=rice_decode_context(raw[2],ictx,16)
    else:ss=leb_dec(raw[2],nr-nn);inter=restore_vals(ss,ictx).astype(np.int32)
    startg=np.empty(nr,np.int32);startg[rf]=firstg;startg[~rf]=inter+2;rows=reconstruct_positions(rc,startg,runlens,T);counts,phase,event_first=metadata_from_positions(rows);ne=int(counts.sum())
    firstsign=np.unpackbits(np.frombuffer(raw[6],np.uint8),bitorder='little',count=nn).astype(bool);rep_mask=~event_first;rsort=np.unpackbits(np.frombuffer(raw[7],np.uint8),bitorder='little',count=ne-nn).astype(bool);repeat=restore_bits(rsort,phase[rep_mask]);signs=np.empty(ne,bool);k=fk=rk=0
    for c0 in counts.tolist():
        c=int(c0)
        if not c:continue
        s=bool(firstsign[fk]);fk+=1;signs[k]=s;k+=1
        for _ in range(1,c):
            if not repeat[rk]:s=not s
            rk+=1;signs[k]=s;k+=1
    if k!=ne or fk!=nn or rk!=repeat.size:raise RuntimeError('Rice sign accounting')
    esort=np.unpackbits(np.frombuffer(raw[8],np.uint8),bitorder='little',count=ne).astype(bool);exc=restore_bits(esort,phase);nex=int(exc.sum());mctx=phase[exc].astype(np.int32)
    if rep9:mag=rice_decode_context(raw[9],mctx,4)
    else:msort=np.frombuffer(raw[9],dtype=DT[dc],count=nex).astype(np.int32) if nex else np.empty(0,np.int32);mag=restore_vals(msort,mctx) if nex else msort
    ab=np.ones(ne,np.int32);ab[exc]=mag+2;vals=np.where(signs,-ab,ab);tr=np.zeros((ntr,T),np.int32);k=0
    for i,pos in enumerate(rows):
        c=pos.size
        if c:tr[i,pos]=vals[k:k+c];k+=c
    if k!=ne:raise RuntimeError('Rice value accounting')
    P=tr.reshape(psh);inv=np.argsort(order);return np.transpose(P,tuple(inv)+(3,))


def encode_frozen_main(K):
    sh,dc,rawframes,meta=prepare_raw_frames(K,ORDER,CTXMODE);frames=[]
    for raw,m in zip(rawframes,FROZEN_METHODS):
        b=comp_one(raw,m)
        if decomp_one(b,m)!=raw:raise RuntimeError('frozen backend roundtrip')
        frames.append(b)
    oc=int(ORDER[0]|(ORDER[1]<<2)|(ORDER[2]<<4));h=struct.pack(HHDR,HMAG,1,oc,dc,CTXMODE,*K.shape,*FROZEN_METHODS,*[len(x) for x in frames]);return h+b''.join(frames)


def decode_outlier(bo,Oshape):
    if bo[1]=='gap':
        A=decode(bo[6]).reshape(Oshape);return undelta(A,1) if bo[2] else A
    A=decode_out_sparse(bo[6]);return undelta(A,1) if bo[2] else A


def main(path,frac):
    X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());public_eps=float(frac)*std;internal_eps=public_eps*INTERNAL_SAFETY;step=2*internal_eps;rawbytes=int(X.nbytes);G,tm,outids,geom=geometry_map(X,gx,gy)
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    O=np.rint(X[outids]/step).astype(np.int32);K=delta(G,3);bo=best_out(O);RO=decode_outlier(bo,O.shape)
    if not np.array_equal(RO,O):raise RuntimeError('outlier exact decode')
    frozen_main=encode_frozen_main(K);frozen_container=int(TOPS)+len(frozen_main)+int(bo[0])
    cache=structural_sequences(K);rows=[]
    for rep2 in (0,1):
        for rep9 in (0,1):
            mb,parts=encode_main_candidate(K,rep2,rep9,cache);RK=decode_main_candidate(mb)
            if not np.array_equal(RK,K):raise RuntimeError(('Rice candidate exact K',rep2,rep9))
            rows.append({'rep_inter_rice':bool(rep2),'rep_magnitude_rice':bool(rep9),'main_bytes':len(mb),'container_bytes':TOP_HS+len(mb)+int(bo[0]),'parts':parts,'blob':mb})
    rows.sort(key=lambda r:r['container_bytes']);best=rows[0];RK=decode_main_candidate(best['blob']);RG=undelta(RK,3);Y=np.empty_like(X)
    for tid,c,l,s in tm:Y[tid]=RG[c,l,s].astype(np.float32)*np.float32(step)
    Y[outids]=RO.astype(np.float32)*np.float32(step);me=float(np.max(np.abs(X-Y)));szb,sze=sz3_bytes(X,public_eps);outblob=bo[6];out_kind=0 if bo[1]=='gap' else 1;tdiff=1 if bo[2] else 0;top=struct.pack(TOP_HDR,TOP_MAGIC,internal_eps,out_kind,tdiff,len(best['blob']),len(outblob))+best['blob']+outblob
    if len(top)!=best['container_bytes']:raise RuntimeError(('top accounting',len(top),best['container_bytes']))
    # Re-decode the actual chosen top-level byte container.
    magic,ee,ok,td,lm,lo=struct.unpack(TOP_HDR,top[:TOP_HS]);p=TOP_HS;RK2=decode_main_candidate(top[p:p+lm]);p+=lm;obb=top[p:p+lo];p+=lo
    if magic!=TOP_MAGIC or p!=len(top) or not np.array_equal(RK2,K):raise RuntimeError('top byte decode')
    if ok==0:A=decode(obb).reshape(O.shape);RO2=undelta(A,1) if td else A
    else:A=decode_out_sparse(obb);RO2=undelta(A,1) if td else A
    if not np.array_equal(RO2,O):raise RuntimeError('top outlier byte decode')
    out={'file':os.path.basename(path),'shape':list(X.shape),'epsilon_fraction_of_std':float(frac),'public_eps':public_eps,'internal_eps':internal_eps,'raw_bytes':rawbytes,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'frozen_container_bytes':frozen_container,'best':{k:v for k,v in best.items() if k!='blob'},'candidates':[{k:v for k,v in r.items() if k!='blob'} for r in rows],'outlier_bytes':int(bo[0]),'container_bytes':len(top),'ratio':float(rawbytes/len(top)),'maxerr':me,'valid':bool(me<=public_eps*(1+3e-6)),'sz3':{'bytes':int(szb),'ratio':float(rawbytes/szb),'maxerr':float(sze)},'gain_vs_direct_sz3':float(szb/len(top)),'improvement_vs_frozen_bytes':int(frozen_container-len(top)),'improvement_vs_frozen_percent':float(100*(frozen_container-len(top))/frozen_container)}
    if not out['valid']:raise RuntimeError(('tight Rice hard error',me,public_eps))
    print(json.dumps({k:out[k] for k in ('epsilon_fraction_of_std','frozen_container_bytes','container_bytes','improvement_vs_frozen_bytes','improvement_vs_frozen_percent','ratio','gain_vs_direct_sz3','K_nonzero_fraction','maxerr','valid')},indent=2),flush=True);print(json.dumps(out['best'],indent=2),flush=True);json.dump(out,open('soda_tight_rice_frames.json','w'),indent=2)

main(sys.argv[1],float(sys.argv[2]))
