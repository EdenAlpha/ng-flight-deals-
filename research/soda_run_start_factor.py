import json,lzma,os,struct,sys
import numpy as np
import zstandard as zstd
import brotli

src=open('research/soda_universal_run_grammar.py').read().split('\ndef main(path):')[0]
exec(compile(src,'soda_universal_run_grammar.py','exec'),globals())

FMAG=b'RSTRT001'
FHDR='<8sBBBB4I10Q'
FHS=struct.calcsize(FHDR)


def zz_enc(a):
    a=np.asarray(a,dtype=np.int64);return ((a<<1)^(a>>63)).astype(np.uint64)

def zz_dec(a):
    u=np.asarray(a,dtype=np.int64);return ((u>>1)^(-(u&1))).astype(np.int32)


def comp_bytes(data,codec):
    if codec==0:return zstd.ZstdCompressor(level=22).compress(data)
    if codec==1:return brotli.compress(data,quality=11,mode=brotli.MODE_GENERIC)
    if codec==2:return lzma.compress(data,format=lzma.FORMAT_XZ,preset=9|lzma.PRESET_EXTREME)
    raise ValueError(codec)

def decomp_bytes(data,codec):
    if codec==0:return zstd.ZstdDecompressor().decompress(data)
    if codec==1:return brotli.decompress(data)
    if codec==2:return lzma.decompress(data,format=lzma.FORMAT_XZ)
    raise ValueError(codec)


def run_first_mask(rc):
    nr=int(np.sum(rc));m=np.zeros(nr,bool);k=0
    for n0 in np.asarray(rc).tolist():
        n=int(n0)
        if n:m[k]=True;k+=n
    if k!=nr:raise RuntimeError('run-first accounting')
    return m


def first_components(rc,order,psh):
    ca=order.index(0);out=[]
    for i,n0 in enumerate(np.asarray(rc).tolist()):
        if int(n0):out.append(int(np.unravel_index(i,psh[:-1])[ca]))
    return np.asarray(out,np.uint8)


def first_payload(firstg,comp,mode):
    a=np.asarray(firstg,np.int32)
    if mode==0:return leb_u(a)
    d=np.empty(a.size,np.int32);prev=0;pc=-1
    for i,x0 in enumerate(a.tolist()):
        x=int(x0);c=int(comp[i])
        if mode==2 and c!=pc:prev=0
        d[i]=x-prev;prev=x;pc=c
    return leb_u(zz_enc(d))

def first_restore(buf,n,comp,mode):
    u=leb_dec(buf,n)
    if mode==0:return u.astype(np.int32)
    d=zz_dec(u);a=np.empty(n,np.int32);prev=0;pc=-1
    for i,x0 in enumerate(d.tolist()):
        c=int(comp[i])
        if mode==2 and c!=pc:prev=0
        prev=prev+int(x0);a[i]=prev;pc=c
    return a


def inter_delta(inter,rc):
    out=[];k=0
    for n0 in np.asarray(rc).tolist():
        m=max(0,int(n0)-1)
        if not m:continue
        v=np.asarray(inter[k:k+m],np.int32);k+=m;d=np.empty(m,np.int32);d[0]=v[0]
        if m>1:d[1:]=np.diff(v)
        out.extend(d.tolist())
    if k!=len(inter):raise RuntimeError('inter delta accounting')
    return np.asarray(out,np.int32)

def inter_undelta(d,rc):
    out=[];k=0
    for n0 in np.asarray(rc).tolist():
        m=max(0,int(n0)-1)
        if not m:continue
        v=np.cumsum(np.asarray(d[k:k+m],np.int32),dtype=np.int64).astype(np.int32);k+=m;out.extend(v.tolist())
    if k!=len(d):raise RuntimeError('inter undelta accounting')
    return np.asarray(out,np.int32)


def encode_inter_raw(inter,rc,mode,codec):
    a=np.asarray(inter,np.int32)
    if mode==0:return comp_bytes(leb_u(a),codec)
    if mode==1:return comp_bytes(leb_u(zz_enc(inter_delta(a,rc))),codec)
    if mode==2:
        nz=a>0;b1=comp_bytes(np.packbits(nz,bitorder='little').tobytes(),codec);b2=comp_bytes(leb_u(a[nz]-1),codec) if nz.any() else b''
        return struct.pack('<II',len(b1),len(b2))+b1+b2
    raise ValueError(mode)

def decode_inter_raw(blob,n,rc,mode,codec):
    if mode==0:return leb_dec(decomp_bytes(blob,codec),n)
    if mode==1:return inter_undelta(zz_dec(leb_dec(decomp_bytes(blob,codec),n)),rc)
    if mode==2:
        if len(blob)<8:raise RuntimeError('tier inter header')
        a,b=struct.unpack('<II',blob[:8]);p=8;b1=blob[p:p+a];p+=a;b2=blob[p:p+b];p+=b
        if p!=len(blob):raise RuntimeError('tier inter length')
        nz=np.unpackbits(np.frombuffer(decomp_bytes(b1,codec),np.uint8),bitorder='little',count=n).astype(bool);vals=leb_dec(decomp_bytes(b2,codec),int(nz.sum())) if nz.any() else np.empty(0,np.int32);out=np.zeros(n,np.int32);out[nz]=vals+1;return out
    raise ValueError(mode)


def encode_main_factor(K,order,codec,firstmode,intermode):
    level=22;zc=zstd.ZstdCompressor(level=level);sh,rc,startg,lens,rcomp,vals,phase,event_first,diag=gather_universal(K,order);nr=lens.size;ne=vals.size;rf=run_first_mask(rc);firstg=startg[rf];inter=startg[~rf]-2
    if np.any(inter<0):raise RuntimeError('inter-run invariant broken')
    firstcomp=rcomp[rf];f0=zc.compress(leb_u(rc));f1=comp_bytes(first_payload(firstg,firstcomp,firstmode),codec);f2=encode_inter_raw(inter,rc,intermode,codec)
    # Freeze #155 winning length grammar: singleton and length-2 implicit.
    long=lens>1;very=lens[long]>2;f3=zc.compress(np.packbits(long,bitorder='little').tobytes());f4=zc.compress(np.packbits(very,bitorder='little').tobytes()) if long.any() else b'';f5=zc.compress(leb_u(lens[long][very]-3)) if very.any() else b''
    # Freeze #154 winning run-phase values exactly.
    signs=vals<0;firstsign=signs[event_first];rep_mask=~event_first;prev=np.empty(ne,bool);k=0;j=0
    for n0 in rc.tolist():
        n=int(n0);c=int(lens[j:j+n].sum()) if n else 0;j+=n
        if c:
            prev[k]=signs[k]
            if c>1:prev[k+1:k+c]=signs[k:k+c-1]
            k+=c
    repeat=(signs==prev)[rep_mask];rsort,_=reorder_bits(repeat,phase[rep_mask]);ab=np.abs(vals);exc=ab!=1;esort,_=reorder_bits(exc,phase);mag=(ab[exc]-2).astype(np.int32);msort,_=reorder_vals(mag,phase[exc]);dc=dtype_code(msort)
    vf=[zc.compress(np.packbits(firstsign,bitorder='little').tobytes()),zc.compress(np.packbits(rsort,bitorder='little').tobytes()),zc.compress(np.packbits(esort,bitorder='little').tobytes()),zc.compress(msort.astype(DT[dc],copy=False).tobytes()) if msort.size else b'']
    frames=[f0,f1,f2,f3,f4,f5,*vf];mode=int(codec+3*firstmode+9*intermode);oc=int(order[0]|(order[1]<<2)|(order[2]<<4));h=struct.pack(FHDR,FMAG,1,oc,dc,mode,*K.shape,*[len(x) for x in frames]);parts={'run_counts':len(f0),'first_starts':len(f1),'inter_starts':len(f2),'long_support':len(f3),'very_support':len(f4),'long_residual':len(f5),'sign_first':len(vf[0]),'sign_repeat':len(vf[1]),'exception_support':len(vf[2]),'exception_magnitude':len(vf[3]),'timing_bytes':sum(len(x) for x in frames[:6]),'value_bytes':sum(len(x) for x in frames[6:]),'codec':['zstd22','brotli11','lzma9e'][codec],'first_mode':['absolute','delta','component-reset-delta'][firstmode],'inter_mode':['gap-minus-2','delta-gap-minus-2','zero-tier-gap-minus-2'][intermode],'first_count':int(firstg.size),'inter_count':int(inter.size),'inter_zero_fraction':float(np.mean(inter==0)) if inter.size else 0.0,**diag}
    return h+b''.join(frames),parts


def decode_main_factor(blob):
    q=struct.unpack(FHDR,blob[:FHS]);magic,ver,oc,dc,mode,C,L,S,T,*lf=q
    if magic!=FMAG or ver!=1:raise RuntimeError('factor header')
    codec=mode%3;firstmode=(mode//3)%3;intermode=mode//9;p=FHS;fs=[]
    for n in lf:fs.append(blob[p:p+n]);p+=n
    if p!=len(blob):raise RuntimeError('factor stream length')
    order=tuple((oc>>(2*i))&3 for i in range(3));shape=(C,L,S,T);psh=tuple(shape[i] for i in order)+(T,);ntr=int(np.prod(psh[:-1]));zd=zstd.ZstdDecompressor();rc=leb_dec(zd.decompress(fs[0]),ntr);nr=int(rc.sum());rf=run_first_mask(rc);nn=int(np.count_nonzero(rc));firstcomp=first_components(rc,order,psh);firstg=first_restore(decomp_bytes(fs[1],codec),nn,firstcomp,firstmode);ni=nr-nn;inter=decode_inter_raw(fs[2],ni,rc,intermode,codec)
    long=np.unpackbits(np.frombuffer(zd.decompress(fs[3]),np.uint8),bitorder='little',count=nr).astype(bool);nl=int(long.sum());very=np.unpackbits(np.frombuffer(zd.decompress(fs[4]),np.uint8),bitorder='little',count=nl).astype(bool) if nl else np.empty(0,bool);res=leb_dec(zd.decompress(fs[5]),int(very.sum())) if very.any() else np.empty(0,np.int32);runlens=np.ones(nr,np.int32);li=np.flatnonzero(long);runlens[li]=2
    if very.any():runlens[li[very]]=res+3
    startg=np.empty(nr,np.int32);startg[rf]=firstg;startg[~rf]=inter+2;rows=reconstruct_positions(rc,startg,runlens,T);counts,phase,event_first=metadata_from_positions(rows);ne=int(counts.sum());firstsign=np.unpackbits(np.frombuffer(zd.decompress(fs[6]),np.uint8),bitorder='little',count=nn).astype(bool);rep_mask=~event_first;rsort=np.unpackbits(np.frombuffer(zd.decompress(fs[7]),np.uint8),bitorder='little',count=ne-nn).astype(bool);repeat=restore_bits(rsort,phase[rep_mask]);signs=np.empty(ne,bool);k=fk=rk=0
    for c0 in counts.tolist():
        c=int(c0)
        if not c:continue
        s=bool(firstsign[fk]);fk+=1;signs[k]=s;k+=1
        for _ in range(1,c):
            if not repeat[rk]:s=not s
            rk+=1;signs[k]=s;k+=1
    if k!=ne or fk!=nn or rk!=repeat.size:raise RuntimeError('factor sign accounting')
    esort=np.unpackbits(np.frombuffer(zd.decompress(fs[8]),np.uint8),bitorder='little',count=ne).astype(bool);exc=restore_bits(esort,phase);nex=int(exc.sum());msort=np.frombuffer(zd.decompress(fs[9]),dtype=DT[dc],count=nex).astype(np.int32) if nex else np.empty(0,np.int32);mag=restore_vals(msort,phase[exc]) if nex else msort;ab=np.ones(ne,np.int32);ab[exc]=mag+2;vals=np.where(signs,-ab,ab);tr=np.zeros((ntr,T),np.int32);k=0
    for i,pos in enumerate(rows):
        c=pos.size
        if c:tr[i,pos]=vals[k:k+c];k+=c
    if k!=ne:raise RuntimeError('factor value accounting')
    P=tr.reshape(psh);inv=np.argsort(order);return np.transpose(P,tuple(inv)+(3,))


def main(path):
    order=(0,1,2);X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());eps=.1*std;step=2*eps;raw=X.nbytes;G,tm,outids,geom=geometry_map(X,gx,gy)
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    O=np.rint(X[outids]/step).astype(np.int32);K=delta(G,3);rows=[]
    for codec in (0,1,2):
      for firstmode in (0,1,2):
       for intermode in (0,1,2):
        b,parts=encode_main_factor(K,order,codec,firstmode,intermode);R=decode_main_factor(b)
        if not np.array_equal(R,K):raise RuntimeError(('factor exact K',codec,firstmode,intermode))
        rows.append({'main_bytes':len(b),'codec':codec,'first_mode':firstmode,'inter_mode':intermode,'parts':parts,'blob':b})
    rows.sort(key=lambda r:r['main_bytes']);best=rows[0];bo=best_out(O);RO=decode_out_best(bo,O.shape)
    if not np.array_equal(RO,O):raise RuntimeError('factor outlier decode')
    RG=undelta(decode_main_factor(best['blob']),3);recon=np.empty_like(X)
    for tid,c,l,s in tm:recon[tid]=RG[c,l,s].astype(np.float32)*np.float32(step)
    recon[outids]=RO.astype(np.float32)*np.float32(step);me=float(np.max(np.abs(X-recon)));szb,sze=sz3_bytes(X,eps);container=TOPS+best['main_bytes']+int(bo[0]);baseline=133225;gate=baseline/2
    out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'eps':eps,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'main_best':{k:v for k,v in best.items() if k!='blob'},'main_candidates':[{k:v for k,v in r.items() if k!='blob'} for r in rows],'outlier_best':{'bytes':int(bo[0]),'kind':bo[1],'tdiff':bool(bo[2]),'mode':int(bo[3]),'level':int(bo[4])},'top_header_bytes':TOPS,'container_bytes':container,'ratio':float(raw/container),'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'sz3':{'bytes':int(szb),'ratio':float(raw/szb),'maxerr':float(sze)},'gain_vs_direct_sz3':float(szb/container),'strongest_verified_p75_baseline_bytes':baseline,'gain_vs_strongest_verified_p75_baseline':float(baseline/container),'two_x_gate_bytes':gate,'prior_record_bytes':68646,'clears_two_x_gate':bool(container<gate)}
    print(json.dumps({k:out[k] for k in ('container_bytes','ratio','maxerr','valid','gain_vs_direct_sz3','gain_vs_strongest_verified_p75_baseline','two_x_gate_bytes','clears_two_x_gate')},indent=2),flush=True);json.dump(out,open('soda_run_start_factor.json','w'),indent=2)

main(sys.argv[1])
