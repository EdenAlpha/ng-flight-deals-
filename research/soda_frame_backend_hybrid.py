import bz2,json,lzma,os,struct,sys,zlib
import numpy as np
import zstandard as zstd

# Reuse PR #155's audited universal-run geometry/timing helpers and PR #154's
# run-phase value semantics.  This experiment changes only the lossless backend
# used for each already-defined frame.
src=open('research/soda_universal_run_grammar.py').read().split('\ndef main(path):')[0]
exec(compile(src,'soda_universal_run_grammar.py','exec'),globals())

HMAG=b'FBHYB001'
HHDR='<8sBBB4I9B9Q'
HHS=struct.calcsize(HHDR)
METHOD_NAMES={0:'raw',1:'zstd22',2:'zstd19',3:'lzma_xz_extreme',4:'bz2_9',5:'zlib_9'}


def comp_one(raw,method):
    if method==0:return raw
    if method==1:return zstd.ZstdCompressor(level=22).compress(raw)
    if method==2:return zstd.ZstdCompressor(level=19).compress(raw)
    if method==3:return lzma.compress(raw,format=lzma.FORMAT_XZ,check=lzma.CHECK_CRC32,preset=9|lzma.PRESET_EXTREME)
    if method==4:return bz2.compress(raw,compresslevel=9)
    if method==5:return zlib.compress(raw,level=9)
    raise ValueError(method)


def decomp_one(blob,method):
    if method==0:return blob
    if method in (1,2):return zstd.ZstdDecompressor().decompress(blob)
    if method==3:return lzma.decompress(blob,format=lzma.FORMAT_XZ)
    if method==4:return bz2.decompress(blob)
    if method==5:return zlib.decompress(blob)
    raise ValueError(method)


def best_comp(raw):
    rows=[]
    for m in range(6):
        b=comp_one(raw,m)
        if decomp_one(b,m)!=raw:raise RuntimeError(('backend roundtrip',m))
        rows.append((len(b),m,b))
    rows.sort(key=lambda x:(x[0],x[1]))
    return rows[0],[(METHOD_NAMES[m],n) for n,m,_ in rows]


def prepare_frames(K,order=(0,1,2)):
    sh,rc,startg,lens,rcomp,vals,phase,event_first,diag=gather_universal(K,order);nr=lens.size;ne=vals.size
    # Freeze PR #155's winning timing grammar: LEB128 run counts, raw start-gap
    # sequence, singleton/length-2 implicit tiered run lengths.
    long=lens>1;very=lens[long]>2
    f0=leb_u(rc)
    f1=leb_u(startg)
    f2=np.packbits(long,bitorder='little').tobytes()
    f3=np.packbits(very,bitorder='little').tobytes() if long.any() else b''
    f4=leb_u(lens[long][very]-3) if very.any() else b''

    # Freeze PR #154/#155's run-phase value semantics exactly.
    signs=vals<0;firstsign=signs[event_first];rep_mask=~event_first;prev=np.empty(ne,bool);k=0;j=0
    for nr0 in rc.tolist():
        n=int(nr0);c=int(lens[j:j+n].sum()) if n else 0;j+=n
        if c:
            prev[k]=signs[k]
            if c>1:prev[k+1:k+c]=signs[k:k+c-1]
            k+=c
    if k!=ne:raise RuntimeError('value trace accounting')
    repeat=(signs==prev)[rep_mask];rsort,_=reorder_bits(repeat,phase[rep_mask])
    ab=np.abs(vals);exc=ab!=1;esort,_=reorder_bits(exc,phase);mag=(ab[exc]-2).astype(np.int32);msort,_=reorder_vals(mag,phase[exc]);dc=dtype_code(msort)
    f5=np.packbits(firstsign,bitorder='little').tobytes()
    f6=np.packbits(rsort,bitorder='little').tobytes()
    f7=np.packbits(esort,bitorder='little').tobytes()
    f8=msort.astype(DT[dc],copy=False).tobytes()
    return sh,dc,[f0,f1,f2,f3,f4,f5,f6,f7,f8],diag


def encode_main(K,order=(0,1,2)):
    sh,dc,rawframes,diag=prepare_frames(K,order);methods=[];frames=[];choices=[]
    for i,r in enumerate(rawframes):
        best,allrows=best_comp(r);n,m,b=best;methods.append(m);frames.append(b);choices.append({'frame':i,'raw_bytes':len(r),'chosen':METHOD_NAMES[m],'bytes':n,'all':allrows})
    oc=int(order[0]|(order[1]<<2)|(order[2]<<4));h=struct.pack(HHDR,HMAG,1,oc,dc,*K.shape,*methods,*[len(x) for x in frames])
    names=['run_counts','run_start_gaps','length_gt1_bits','length_gt2_bits','length_gt3_residuals','sign_first','sign_repeat','exception_support','exception_magnitude']
    parts={names[i]:len(frames[i]) for i in range(9)};parts['timing_bytes']=sum(len(x) for x in frames[:5]);parts['value_bytes']=sum(len(x) for x in frames[5:]);parts['header_bytes']=HHS;parts['backend_choices']=choices;parts.update(diag)
    return h+b''.join(frames),parts


def decode_main(blob):
    q=struct.unpack(HHDR,blob[:HHS]);magic,ver,oc,dc,C,L,S,T,*rest=q
    if magic!=HMAG or ver!=1:raise RuntimeError('hybrid header')
    methods=rest[:9];lensf=rest[9:];p=HHS;frames=[]
    for n in lensf:frames.append(blob[p:p+n]);p+=n
    if p!=len(blob):raise RuntimeError('hybrid stream length')
    raw=[decomp_one(frames[i],methods[i]) for i in range(9)]
    order=tuple((oc>>(2*i))&3 for i in range(3));shape=(C,L,S,T);psh=tuple(shape[i] for i in order)+(T,);ntr=int(np.prod(psh[:-1]))
    rc=leb_dec(raw[0],ntr);nr=int(rc.sum())
    long=np.unpackbits(np.frombuffer(raw[2],np.uint8),bitorder='little',count=nr).astype(bool);nl=int(long.sum())
    very=np.unpackbits(np.frombuffer(raw[3],np.uint8),bitorder='little',count=nl).astype(bool) if nl else np.empty(0,bool)
    resid=leb_dec(raw[4],int(very.sum())) if very.any() else np.empty(0,np.int32)
    runlens=np.ones(nr,np.int32);li=np.flatnonzero(long);runlens[li]=2
    if very.any():runlens[li[very]]=resid+3
    startg=leb_dec(raw[1],nr);rows=reconstruct_positions(rc,startg,runlens,T);counts,phase,event_first=metadata_from_positions(rows);ne=int(counts.sum());nn=int(np.count_nonzero(counts))
    firstsign=np.unpackbits(np.frombuffer(raw[5],np.uint8),bitorder='little',count=nn).astype(bool);rep_mask=~event_first
    rsort=np.unpackbits(np.frombuffer(raw[6],np.uint8),bitorder='little',count=ne-nn).astype(bool);repeat=restore_bits(rsort,phase[rep_mask]);signs=np.empty(ne,bool);k=fk=rk=0
    for c0 in counts.tolist():
        c=int(c0)
        if not c:continue
        s=bool(firstsign[fk]);fk+=1;signs[k]=s;k+=1
        for _ in range(1,c):
            if not repeat[rk]:s=not s
            rk+=1;signs[k]=s;k+=1
    if k!=ne or fk!=nn or rk!=repeat.size:raise RuntimeError('hybrid sign accounting')
    esort=np.unpackbits(np.frombuffer(raw[7],np.uint8),bitorder='little',count=ne).astype(bool);exc=restore_bits(esort,phase);nex=int(exc.sum())
    msort=np.frombuffer(raw[8],dtype=DT[dc],count=nex).astype(np.int32) if nex else np.empty(0,np.int32);mag=restore_vals(msort,phase[exc]) if nex else msort;ab=np.ones(ne,np.int32);ab[exc]=mag+2;vals=np.where(signs,-ab,ab)
    tr=np.zeros((ntr,T),np.int32);k=0
    for i,pos in enumerate(rows):
        c=pos.size
        if c:tr[i,pos]=vals[k:k+c];k+=c
    if k!=ne:raise RuntimeError('hybrid value accounting')
    P=tr.reshape(psh);inv=np.argsort(order);return np.transpose(P,tuple(inv)+(3,))


def main(path):
    order=(0,1,2);X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());eps=.1*std;step=2*eps;rawbytes=X.nbytes;G,tm,outids,geom=geometry_map(X,gx,gy)
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    O=np.rint(X[outids]/step).astype(np.int32);K=delta(G,3);mb,parts=encode_main(K,order);RK=decode_main(mb)
    if not np.array_equal(RK,K):raise RuntimeError('hybrid main exact decode')
    bo=best_out(O);RO=decode_out_best(bo,O.shape)
    if not np.array_equal(RO,O):raise RuntimeError('hybrid outlier exact decode')
    RG=undelta(RK,3);recon=np.empty_like(X)
    for tid,c,l,s in tm:recon[tid]=RG[c,l,s].astype(np.float32)*np.float32(step)
    recon[outids]=RO.astype(np.float32)*np.float32(step);me=float(np.max(np.abs(X-recon)));szb,sze=sz3_bytes(X,eps);container=TOPS+len(mb)+int(bo[0]);baseline=133225;gate=baseline/2
    out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':rawbytes,'eps':eps,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'main_bytes':len(mb),'main_parts':parts,'outlier_bytes':int(bo[0]),'top_header_bytes':TOPS,'container_bytes':container,'ratio':rawbytes/container,'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'sz3':{'bytes':int(szb),'ratio':rawbytes/szb,'maxerr':float(sze)},'gain_vs_direct_sz3':float(szb/container),'strongest_verified_p75_baseline_bytes':baseline,'gain_vs_strongest_verified_p75_baseline':float(baseline/container),'two_x_gate_bytes':gate,'prior_record_bytes':68646,'clears_two_x_gate':bool(container<=gate)}
    print(json.dumps(out,indent=2),flush=True);json.dump(out,open('soda_frame_backend_hybrid.json','w'),indent=2)

main(sys.argv[1])
