import json,os,struct,sys
import numpy as np
import zstandard as zstd
import brotli

src=open('research/soda_run_start_factor.py').read().split('\ndef main(path):')[0]
exec(compile(src,'soda_run_start_factor.py','exec'),globals())

IMAG=b'IGCTX001'
IHDR='<8sBBBB4I10Q'
IHS=struct.calcsize(IHDR)


def lenclass(x):
    x=int(x)
    return 0 if x==1 else (1 if x==2 else (2 if x==3 else 3))


def inter_context(rc,lens,rcomp,mode):
    out=[];k=0
    for n0 in np.asarray(rc).tolist():
        n=int(n0)
        if n:
            comp=int(rcomp[k])
            for j in range(1,n):
                a=int(lens[k+j-1]);b=int(lens[k+j]);pa=1 if a>1 else 0;pb=1 if b>1 else 0;pair=pa*2+pb;lc=lenclass(a)*4+lenclass(b);rb=0 if j==1 else (1 if j==2 else (2 if j<=4 else 3))
                if mode==0:c=0
                elif mode==1:c=comp
                elif mode==2:c=pair
                elif mode==3:c=comp*4+pair
                elif mode==4:c=lc
                elif mode==5:c=comp*16+lc
                elif mode==6:c=rb
                elif mode==7:c=comp*4+rb
                elif mode==8:c=rb*4+pair
                else:raise ValueError(mode)
                out.append(c)
            k+=n
    if k!=len(lens):raise RuntimeError('inter context run accounting')
    return np.asarray(out,np.int32)


def context_diag(ctx,inter):
    rows=[]
    for c in np.unique(ctx).tolist():
        a=np.asarray(inter)[ctx==c];rows.append({'id':int(c),'n':int(a.size),'zero_fraction':float(np.mean(a==0)) if a.size else 0.0,'mean':float(np.mean(a)) if a.size else 0.0,'median':float(np.median(a)) if a.size else 0.0})
    return rows


def encode_ctx_inter(inter,ctx,style):
    a=np.asarray(inter,np.int32);ctx=np.asarray(ctx,np.int32)
    if style==0:
        s,_=reorder_vals(a,ctx);return brotli.compress(leb_u(s),quality=11,mode=brotli.MODE_GENERIC)
    nctx=int(ctx.max())+1 if ctx.size else 0;chunks=[]
    for c in range(nctx):chunks.append(brotli.compress(leb_u(a[ctx==c]),quality=11,mode=brotli.MODE_GENERIC) if np.any(ctx==c) else b'')
    return bytes([nctx])+b''.join(struct.pack('<I',len(x)) for x in chunks)+b''.join(chunks)


def decode_ctx_inter(blob,n,ctx,style):
    ctx=np.asarray(ctx,np.int32)
    if style==0:
        s=leb_dec(brotli.decompress(blob),n);return restore_vals(s,ctx).astype(np.int32)
    if not blob:raise RuntimeError('empty split context blob')
    nctx=blob[0];p=1
    if len(blob)<1+4*nctx:raise RuntimeError('short split context header')
    lens=[]
    for _ in range(nctx):lens.append(struct.unpack('<I',blob[p:p+4])[0]);p+=4
    groups=[]
    for c,L in enumerate(lens):
        b=blob[p:p+L];p+=L;cnt=int(np.sum(ctx==c));groups.append(leb_dec(brotli.decompress(b),cnt) if cnt else np.empty(0,np.int32))
    if p!=len(blob):raise RuntimeError('split context trailing bytes')
    out=np.empty(n,np.int32)
    for c,g in enumerate(groups):out[ctx==c]=g
    return out


def encode_main_ctx(K,order,ctxmode,style):
    zc=zstd.ZstdCompressor(level=22);sh,rc,startg,lens,rcomp,vals,phase,event_first,diag=gather_universal(K,order);nr=lens.size;ne=vals.size;rf=run_first_mask(rc);firstg=startg[rf];inter=startg[~rf]-2
    if np.any(inter<0):raise RuntimeError('inter invariant')
    firstcomp=rcomp[rf];f0=zc.compress(leb_u(rc));f1=brotli.compress(first_payload(firstg,firstcomp,2),quality=11,mode=brotli.MODE_GENERIC);ictx=inter_context(rc,lens,rcomp,ctxmode)
    if ictx.size!=inter.size:raise RuntimeError('inter context size')
    f2=encode_ctx_inter(inter,ictx,style)
    long=lens>1;very=lens[long]>2;f3=zc.compress(np.packbits(long,bitorder='little').tobytes());f4=zc.compress(np.packbits(very,bitorder='little').tobytes()) if long.any() else b'';f5=zc.compress(leb_u(lens[long][very]-3)) if very.any() else b''
    signs=vals<0;firstsign=signs[event_first];rep_mask=~event_first;prev=np.empty(ne,bool);k=0;j=0
    for n0 in rc.tolist():
        n=int(n0);c=int(lens[j:j+n].sum()) if n else 0;j+=n
        if c:
            prev[k]=signs[k]
            if c>1:prev[k+1:k+c]=signs[k:k+c-1]
            k+=c
    repeat=(signs==prev)[rep_mask];rsort,_=reorder_bits(repeat,phase[rep_mask]);ab=np.abs(vals);exc=ab!=1;esort,_=reorder_bits(exc,phase);mag=(ab[exc]-2).astype(np.int32);msort,_=reorder_vals(mag,phase[exc]);dc=dtype_code(msort);vf=[zc.compress(np.packbits(firstsign,bitorder='little').tobytes()),zc.compress(np.packbits(rsort,bitorder='little').tobytes()),zc.compress(np.packbits(esort,bitorder='little').tobytes()),zc.compress(msort.astype(DT[dc],copy=False).tobytes()) if msort.size else b'']
    frames=[f0,f1,f2,f3,f4,f5,*vf];code=int(ctxmode+16*style);oc=int(order[0]|(order[1]<<2)|(order[2]<<4));h=struct.pack(IHDR,IMAG,1,oc,dc,code,*K.shape,*[len(x) for x in frames]);parts={'run_counts':len(f0),'first_starts':len(f1),'inter_starts':len(f2),'long_support':len(f3),'very_support':len(f4),'long_residual':len(f5),'sign_first':len(vf[0]),'sign_repeat':len(vf[1]),'exception_support':len(vf[2]),'exception_magnitude':len(vf[3]),'timing_bytes':sum(len(x) for x in frames[:6]),'value_bytes':sum(len(x) for x in frames[6:]),'context_mode':ctxmode,'context_style':['reorder-one-frame','split-frames'][style],'context_stats':context_diag(ictx,inter),'inter_zero_fraction':float(np.mean(inter==0)) if inter.size else 0.0,**diag}
    return h+b''.join(frames),parts


def decode_main_ctx(blob):
    q=struct.unpack(IHDR,blob[:IHS]);magic,ver,oc,dc,code,C,L,S,T,*lf=q
    if magic!=IMAG or ver!=1:raise RuntimeError('inter context header')
    ctxmode=code%16;style=code//16;p=IHS;fs=[]
    for n in lf:fs.append(blob[p:p+n]);p+=n
    if p!=len(blob):raise RuntimeError('inter context stream length')
    order=tuple((oc>>(2*i))&3 for i in range(3));shape=(C,L,S,T);psh=tuple(shape[i] for i in order)+(T,);ntr=int(np.prod(psh[:-1]));zd=zstd.ZstdDecompressor();rc=leb_dec(zd.decompress(fs[0]),ntr);nr=int(rc.sum());rf=run_first_mask(rc);nn=int(np.count_nonzero(rc));firstcomp=first_components(rc,order,psh);firstg=first_restore(brotli.decompress(fs[1]),nn,firstcomp,2)
    long=np.unpackbits(np.frombuffer(zd.decompress(fs[3]),np.uint8),bitorder='little',count=nr).astype(bool);nl=int(long.sum());very=np.unpackbits(np.frombuffer(zd.decompress(fs[4]),np.uint8),bitorder='little',count=nl).astype(bool) if nl else np.empty(0,bool);res=leb_dec(zd.decompress(fs[5]),int(very.sum())) if very.any() else np.empty(0,np.int32);runlens=np.ones(nr,np.int32);li=np.flatnonzero(long);runlens[li]=2
    if very.any():runlens[li[very]]=res+3
    rcomp=run_components(rc,order,psh);ictx=inter_context(rc,runlens,rcomp,ctxmode);inter=decode_ctx_inter(fs[2],nr-nn,ictx,style);startg=np.empty(nr,np.int32);startg[rf]=firstg;startg[~rf]=inter+2;rows=reconstruct_positions(rc,startg,runlens,T);counts,phase,event_first=metadata_from_positions(rows);ne=int(counts.sum());firstsign=np.unpackbits(np.frombuffer(zd.decompress(fs[6]),np.uint8),bitorder='little',count=nn).astype(bool);rep_mask=~event_first;rsort=np.unpackbits(np.frombuffer(zd.decompress(fs[7]),np.uint8),bitorder='little',count=ne-nn).astype(bool);repeat=restore_bits(rsort,phase[rep_mask]);signs=np.empty(ne,bool);k=fk=rk=0
    for c0 in counts.tolist():
        c=int(c0)
        if not c:continue
        s=bool(firstsign[fk]);fk+=1;signs[k]=s;k+=1
        for _ in range(1,c):
            if not repeat[rk]:s=not s
            rk+=1;signs[k]=s;k+=1
    if k!=ne or fk!=nn or rk!=repeat.size:raise RuntimeError('inter context sign accounting')
    esort=np.unpackbits(np.frombuffer(zd.decompress(fs[8]),np.uint8),bitorder='little',count=ne).astype(bool);exc=restore_bits(esort,phase);nex=int(exc.sum());msort=np.frombuffer(zd.decompress(fs[9]),dtype=DT[dc],count=nex).astype(np.int32) if nex else np.empty(0,np.int32);mag=restore_vals(msort,phase[exc]) if nex else msort;ab=np.ones(ne,np.int32);ab[exc]=mag+2;vals=np.where(signs,-ab,ab);tr=np.zeros((ntr,T),np.int32);k=0
    for i,pos in enumerate(rows):
        c=pos.size
        if c:tr[i,pos]=vals[k:k+c];k+=c
    if k!=ne:raise RuntimeError('inter context value accounting')
    P=tr.reshape(psh);inv=np.argsort(order);return np.transpose(P,tuple(inv)+(3,))


def main(path):
    order=(0,1,2);X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());eps=.1*std;step=2*eps;raw=X.nbytes;G,tm,outids,geom=geometry_map(X,gx,gy)
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    O=np.rint(X[outids]/step).astype(np.int32);K=delta(G,3);rows=[]
    for ctxmode in range(9):
      for style in (0,1):
        b,parts=encode_main_ctx(K,order,ctxmode,style);R=decode_main_ctx(b)
        if not np.array_equal(R,K):raise RuntimeError(('inter context exact K',ctxmode,style))
        rows.append({'main_bytes':len(b),'context_mode':ctxmode,'style':style,'parts':parts,'blob':b})
    rows.sort(key=lambda r:r['main_bytes']);best=rows[0];bo=best_out(O);RO=decode_out_best(bo,O.shape)
    if not np.array_equal(RO,O):raise RuntimeError('inter context outlier decode')
    RG=undelta(decode_main_ctx(best['blob']),3);recon=np.empty_like(X)
    for tid,c,l,s in tm:recon[tid]=RG[c,l,s].astype(np.float32)*np.float32(step)
    recon[outids]=RO.astype(np.float32)*np.float32(step);me=float(np.max(np.abs(X-recon)));szb,sze=sz3_bytes(X,eps);container=TOPS+best['main_bytes']+int(bo[0]);baseline=133225;gate=baseline/2
    out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'eps':eps,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'main_best':{k:v for k,v in best.items() if k!='blob'},'main_candidates':[{k:v for k,v in r.items() if k!='blob'} for r in rows],'outlier_best':{'bytes':int(bo[0]),'kind':bo[1],'tdiff':bool(bo[2]),'mode':int(bo[3]),'level':int(bo[4])},'top_header_bytes':TOPS,'container_bytes':container,'ratio':float(raw/container),'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'sz3':{'bytes':int(szb),'ratio':float(raw/szb),'maxerr':float(sze)},'gain_vs_direct_sz3':float(szb/container),'strongest_verified_p75_baseline_bytes':baseline,'gain_vs_strongest_verified_p75_baseline':float(baseline/container),'two_x_gate_bytes':gate,'prior_record_bytes':65740,'clears_two_x_gate':bool(container<gate)}
    print(json.dumps({k:out[k] for k in ('container_bytes','ratio','maxerr','valid','gain_vs_direct_sz3','gain_vs_strongest_verified_p75_baseline','clears_two_x_gate')},indent=2),flush=True);json.dump(out,open('soda_intergap_context.json','w'),indent=2)

main(sys.argv[1])
