import bz2,json,lzma,os,struct,sys,zlib
import numpy as np
import zstandard as zstd
import brotli

# Reuse PR #158's exact structural contexts and all earlier audited geometry,
# run, value, outlier, and fidelity logic. This experiment changes only the
# lossless backend chosen for each already-defined frame.
src=open('research/soda_intergap_context.py').read().split('\ndef main(path):')[0]
exec(compile(src,'soda_intergap_context.py','exec'),globals())

HMAG=b'IGHYB001'
HHDR='<8sBBBB4I10B10Q'
HHS=struct.calcsize(HHDR)
METHOD_NAMES={0:'raw',1:'zstd22',2:'zstd19',3:'brotli11',4:'lzma_xz_extreme',5:'bz2_9',6:'zlib_9'}


def comp_one(raw,m):
    if m==0:return raw
    if m==1:return zstd.ZstdCompressor(level=22).compress(raw)
    if m==2:return zstd.ZstdCompressor(level=19).compress(raw)
    if m==3:return brotli.compress(raw,quality=11,mode=brotli.MODE_GENERIC)
    if m==4:return lzma.compress(raw,format=lzma.FORMAT_XZ,check=lzma.CHECK_CRC32,preset=9|lzma.PRESET_EXTREME)
    if m==5:return bz2.compress(raw,compresslevel=9)
    if m==6:return zlib.compress(raw,level=9)
    raise ValueError(m)


def decomp_one(blob,m):
    if m==0:return blob
    if m in (1,2):return zstd.ZstdDecompressor().decompress(blob)
    if m==3:return brotli.decompress(blob)
    if m==4:return lzma.decompress(blob,format=lzma.FORMAT_XZ)
    if m==5:return bz2.decompress(blob)
    if m==6:return zlib.decompress(blob)
    raise ValueError(m)


def best_comp(raw):
    rows=[]
    for m in range(7):
        b=comp_one(raw,m)
        if decomp_one(b,m)!=raw:raise RuntimeError(('backend roundtrip',m))
        rows.append((len(b),m,b))
    rows.sort(key=lambda x:(x[0],x[1]));return rows[0],[(METHOD_NAMES[m],n) for n,m,_ in rows]


def prepare_raw_frames(K,order=(0,1,2),ctxmode=4):
    sh,rc,startg,lens,rcomp,vals,phase,event_first,diag=gather_universal(K,order);nr=lens.size;ne=vals.size;rf=run_first_mask(rc);firstg=startg[rf];inter=startg[~rf]-2
    if np.any(inter<0):raise RuntimeError('inter invariant')
    firstcomp=rcomp[rf];ictx=inter_context(rc,lens,rcomp,ctxmode);s,_=reorder_vals(inter,ictx)
    long=lens>1;very=lens[long]>2
    f0=leb_u(rc);f1=first_payload(firstg,firstcomp,2);f2=leb_u(s);f3=np.packbits(long,bitorder='little').tobytes();f4=np.packbits(very,bitorder='little').tobytes() if long.any() else b'';f5=leb_u(lens[long][very]-3) if very.any() else b''
    signs=vals<0;firstsign=signs[event_first];rep_mask=~event_first;prev=np.empty(ne,bool);k=0;j=0
    for n0 in rc.tolist():
        n=int(n0);c=int(lens[j:j+n].sum()) if n else 0;j+=n
        if c:
            prev[k]=signs[k]
            if c>1:prev[k+1:k+c]=signs[k:k+c-1]
            k+=c
    if k!=ne:raise RuntimeError('value trace accounting')
    repeat=(signs==prev)[rep_mask];rsort,_=reorder_bits(repeat,phase[rep_mask]);ab=np.abs(vals);exc=ab!=1;esort,_=reorder_bits(exc,phase);mag=(ab[exc]-2).astype(np.int32);msort,_=reorder_vals(mag,phase[exc]);dc=dtype_code(msort)
    f6=np.packbits(firstsign,bitorder='little').tobytes();f7=np.packbits(rsort,bitorder='little').tobytes();f8=np.packbits(esort,bitorder='little').tobytes();f9=msort.astype(DT[dc],copy=False).tobytes()
    meta={'context_mode':ctxmode,'context_stats':context_diag(ictx,inter),'first_count':int(firstg.size),'inter_count':int(inter.size),'inter_zero_fraction':float(np.mean(inter==0)) if inter.size else 0.0,**diag}
    return sh,dc,[f0,f1,f2,f3,f4,f5,f6,f7,f8,f9],meta


def encode_main(K,order=(0,1,2),ctxmode=4):
    sh,dc,rawframes,meta=prepare_raw_frames(K,order,ctxmode);methods=[];frames=[];choices=[]
    for i,r in enumerate(rawframes):
        best,allrows=best_comp(r);n,m,b=best;methods.append(m);frames.append(b);choices.append({'frame':i,'raw_bytes':len(r),'chosen':METHOD_NAMES[m],'bytes':n,'all':allrows})
    oc=int(order[0]|(order[1]<<2)|(order[2]<<4));code=int(ctxmode);h=struct.pack(HHDR,HMAG,1,oc,dc,code,*K.shape,*methods,*[len(x) for x in frames])
    names=['run_counts','first_starts','inter_starts','long_support','very_support','long_residual','sign_first','sign_repeat','exception_support','exception_magnitude'];parts={names[i]:len(frames[i]) for i in range(10)};parts['timing_bytes']=sum(len(x) for x in frames[:6]);parts['value_bytes']=sum(len(x) for x in frames[6:]);parts['header_bytes']=HHS;parts['backend_choices']=choices;parts.update(meta)
    return h+b''.join(frames),parts


def decode_main(blob):
    q=struct.unpack(HHDR,blob[:HHS]);magic,ver,oc,dc,code,C,L,S,T,*rest=q
    if magic!=HMAG or ver!=1:raise RuntimeError('hybrid context header')
    ctxmode=int(code);methods=rest[:10];lf=rest[10:];p=HHS;frames=[]
    for n in lf:frames.append(blob[p:p+n]);p+=n
    if p!=len(blob):raise RuntimeError('hybrid context stream length')
    raw=[decomp_one(frames[i],methods[i]) for i in range(10)]
    order=tuple((oc>>(2*i))&3 for i in range(3));shape=(C,L,S,T);psh=tuple(shape[i] for i in order)+(T,);ntr=int(np.prod(psh[:-1]));rc=leb_dec(raw[0],ntr);nr=int(rc.sum());rf=run_first_mask(rc);nn=int(np.count_nonzero(rc));firstcomp=first_components(rc,order,psh);firstg=first_restore(raw[1],nn,firstcomp,2)
    long=np.unpackbits(np.frombuffer(raw[3],np.uint8),bitorder='little',count=nr).astype(bool);nl=int(long.sum());very=np.unpackbits(np.frombuffer(raw[4],np.uint8),bitorder='little',count=nl).astype(bool) if nl else np.empty(0,bool);res=leb_dec(raw[5],int(very.sum())) if very.any() else np.empty(0,np.int32);runlens=np.ones(nr,np.int32);li=np.flatnonzero(long);runlens[li]=2
    if very.any():runlens[li[very]]=res+3
    rcomp=run_components(rc,order,psh);ictx=inter_context(rc,runlens,rcomp,ctxmode);ss=leb_dec(raw[2],nr-nn);inter=restore_vals(ss,ictx).astype(np.int32);startg=np.empty(nr,np.int32);startg[rf]=firstg;startg[~rf]=inter+2;rows=reconstruct_positions(rc,startg,runlens,T);counts,phase,event_first=metadata_from_positions(rows);ne=int(counts.sum())
    firstsign=np.unpackbits(np.frombuffer(raw[6],np.uint8),bitorder='little',count=nn).astype(bool);rep_mask=~event_first;rsort=np.unpackbits(np.frombuffer(raw[7],np.uint8),bitorder='little',count=ne-nn).astype(bool);repeat=restore_bits(rsort,phase[rep_mask]);signs=np.empty(ne,bool);k=fk=rk=0
    for c0 in counts.tolist():
        c=int(c0)
        if not c:continue
        s=bool(firstsign[fk]);fk+=1;signs[k]=s;k+=1
        for _ in range(1,c):
            if not repeat[rk]:s=not s
            rk+=1;signs[k]=s;k+=1
    if k!=ne or fk!=nn or rk!=repeat.size:raise RuntimeError('hybrid context sign accounting')
    esort=np.unpackbits(np.frombuffer(raw[8],np.uint8),bitorder='little',count=ne).astype(bool);exc=restore_bits(esort,phase);nex=int(exc.sum());msort=np.frombuffer(raw[9],dtype=DT[dc],count=nex).astype(np.int32) if nex else np.empty(0,np.int32);mag=restore_vals(msort,phase[exc]) if nex else msort;ab=np.ones(ne,np.int32);ab[exc]=mag+2;vals=np.where(signs,-ab,ab);tr=np.zeros((ntr,T),np.int32);k=0
    for i,pos in enumerate(rows):
        c=pos.size
        if c:tr[i,pos]=vals[k:k+c];k+=c
    if k!=ne:raise RuntimeError('hybrid context value accounting')
    P=tr.reshape(psh);inv=np.argsort(order);return np.transpose(P,tuple(inv)+(3,))


def main(path):
    order=(0,1,2);ctxmode=4;X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());eps=.1*std;step=2*eps;rawbytes=X.nbytes;G,tm,outids,geom=geometry_map(X,gx,gy)
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    O=np.rint(X[outids]/step).astype(np.int32);K=delta(G,3);mb,parts=encode_main(K,order,ctxmode);RK=decode_main(mb)
    if not np.array_equal(RK,K):raise RuntimeError('hybrid context exact K')
    bo=best_out(O);RO=decode_out_best(bo,O.shape)
    if not np.array_equal(RO,O):raise RuntimeError('hybrid context outlier decode')
    RG=undelta(RK,3);recon=np.empty_like(X)
    for tid,c,l,s in tm:recon[tid]=RG[c,l,s].astype(np.float32)*np.float32(step)
    recon[outids]=RO.astype(np.float32)*np.float32(step);me=float(np.max(np.abs(X-recon)));szb,sze=sz3_bytes(X,eps);container=TOPS+len(mb)+int(bo[0]);baseline=133225;gate=baseline/2
    out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':rawbytes,'eps':eps,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'main_bytes':len(mb),'main_parts':parts,'outlier_bytes':int(bo[0]),'top_header_bytes':TOPS,'container_bytes':container,'ratio':float(rawbytes/container),'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'sz3':{'bytes':int(szb),'ratio':float(rawbytes/szb),'maxerr':float(sze)},'gain_vs_direct_sz3':float(szb/container),'strongest_verified_p75_baseline_bytes':baseline,'gain_vs_strongest_verified_p75_baseline':float(baseline/container),'two_x_gate_bytes':gate,'prior_record_bytes':65715,'clears_two_x_gate':bool(container<gate)}
    print(json.dumps({k:out[k] for k in ('container_bytes','ratio','maxerr','valid','gain_vs_direct_sz3','gain_vs_strongest_verified_p75_baseline','clears_two_x_gate')},indent=2),flush=True);json.dump(out,open('soda_intergap_backend_hybrid.json','w'),indent=2)

main(sys.argv[1])
