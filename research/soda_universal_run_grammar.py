import json,os,struct,sys
import numpy as np
import zstandard as zstd

# Reuse the audited p75 loader/geometry/outlier codec and the PR #154
# run-phase value semantics.  This experiment changes ONLY main-grid timing.
src=open('research/soda_run_aware_values.py').read().split('\ndef main(path):')[0]
exec(compile(src,'soda_run_aware_values.py','exec'),globals())

UMAG=b'URUNv001'
UHDR='<8sBBBBBB4I9Q'
UHS=struct.calcsize(UHDR)
TOP='<8sdQQB'
TOPS=struct.calcsize(TOP)


def leb_u(a):
    out=bytearray()
    for x0 in np.asarray(a).ravel().tolist():
        x=int(x0)
        if x<0: raise ValueError('negative unsigned LEB128')
        while True:
            b=x&127;x>>=7
            if x: out.append(b|128)
            else: out.append(b);break
    return bytes(out)


def leb_dec(buf,n):
    out=np.empty(n,np.int32);p=0
    for i in range(n):
        x=0;s=0
        while True:
            if p>=len(buf):raise RuntimeError('short LEB128')
            b=buf[p];p+=1;x|=(b&127)<<s
            if not (b&128):break
            s+=7
            if s>28:raise RuntimeError('LEB128 overflow')
        out[i]=x
    if p!=len(buf):raise RuntimeError(('LEB128 trailing bytes',p,len(buf)))
    return out


def gather_universal(K,order):
    P=np.transpose(K,order+(3,));sh=P.shape;tr=P.reshape(-1,sh[-1]);ntr=tr.shape[0]
    rc=np.zeros(ntr,np.uint16);startg=[];lens=[];vals=[];phases=[];first=[];runcomp=[]
    comp_axis=order.index(0);spatial_shape=sh[:-1];adj=0
    for i,row in enumerate(tr):
        pos=np.flatnonzero(row);c=pos.size
        if not c:continue
        starts,ll=trace_runs(pos);nr=starts.size;rc[i]=nr;adj+=c-nr
        coord=np.unravel_index(i,spatial_shape);comp=int(coord[comp_axis]);runcomp.extend([comp]*nr)
        prev=-1
        for st,ln in zip(starts.tolist(),ll.tolist()):
            startg.append(int(st)-prev);lens.append(int(ln));prev=int(st)+int(ln)-1
        vals.extend(row[pos].astype(np.int32).tolist());phases.extend(phase_labels(pos).tolist())
        fm=np.zeros(c,bool);fm[0]=True;first.extend(fm.tolist())
    vals=np.asarray(vals,np.int32);phases=np.asarray(phases,np.uint8);first=np.asarray(first,bool)
    startg=np.asarray(startg,np.int32);lens=np.asarray(lens,np.int32);runcomp=np.asarray(runcomp,np.uint8)
    if lens.size!=int(rc.sum()) or lens.sum()!=vals.size or phases.size!=vals.size or first.size!=vals.size:raise RuntimeError('universal gather accounting')
    return sh,rc,startg,lens,runcomp,vals,phases,first,{'runs':int(lens.size),'events':int(vals.size),'adjacent_events':int(adj),'adjacent_fraction':float(adj/max(1,vals.size)),'long_runs':int(np.sum(lens>1)),'len2_runs':int(np.sum(lens==2)),'len3_runs':int(np.sum(lens==3)),'max_run':int(lens.max()) if lens.size else 0}


def run_components(rc,order,psh):
    comp_axis=order.index(0);out=[]
    for i,n0 in enumerate(rc.tolist()):
        n=int(n0)
        if n:
            coord=np.unravel_index(i,psh[:-1]);out.extend([int(coord[comp_axis])]*n)
    return np.asarray(out,np.uint8)


def start_context(comp,lens,mode):
    long=(np.asarray(lens)>1).astype(np.int32);comp=np.asarray(comp,np.int32)
    if mode==0:return np.zeros(long.size,np.int32)
    if mode==1:return long
    if mode==2:return comp
    if mode==3:return comp*2+long
    raise ValueError(mode)


def decode_lengths(grammar,fs,nr,zd):
    if grammar==0:
        lens=leb_dec(zd.decompress(fs[2]),nr)
    elif grammar==1:
        long=np.unpackbits(np.frombuffer(zd.decompress(fs[2]),np.uint8),bitorder='little',count=nr).astype(bool)
        extra=leb_dec(zd.decompress(fs[3]),int(long.sum())) if long.any() else np.empty(0,np.int32)
        lens=np.ones(nr,np.int32);lens[long]=extra+2
    elif grammar==2:
        long=np.unpackbits(np.frombuffer(zd.decompress(fs[2]),np.uint8),bitorder='little',count=nr).astype(bool);nl=int(long.sum())
        very=np.unpackbits(np.frombuffer(zd.decompress(fs[3]),np.uint8),bitorder='little',count=nl).astype(bool) if nl else np.empty(0,bool)
        resid=leb_dec(zd.decompress(fs[4]),int(very.sum())) if very.any() else np.empty(0,np.int32)
        lens=np.ones(nr,np.int32);li=np.flatnonzero(long);lens[li]=2
        if very.any():lens[li[very]]=resid+3
    else:raise RuntimeError('bad grammar')
    if lens.size!=nr or np.any(lens<=0):raise RuntimeError('bad run lengths')
    return lens


def reconstruct_positions(rc,startg,lens,T):
    rows=[];k=0
    for nr0 in rc.tolist():
        nr=int(nr0);pos=[];prev=-1
        for _ in range(nr):
            st=prev+int(startg[k]);ln=int(lens[k]);k+=1
            if st<0 or st+ln>T:raise RuntimeError(('run bounds',st,ln,T))
            pos.extend(range(st,st+ln));prev=st+ln-1
        rows.append(np.asarray(pos,np.int32))
    if k!=lens.size:raise RuntimeError('run reconstruction accounting')
    return rows


def metadata_from_positions(rows):
    phase=[];first=[];counts=np.zeros(len(rows),np.int32)
    for i,pos in enumerate(rows):
        c=pos.size;counts[i]=c
        if c:
            phase.extend(phase_labels(pos).tolist());fm=np.zeros(c,bool);fm[0]=True;first.extend(fm.tolist())
    return counts,np.asarray(phase,np.uint8),np.asarray(first,bool)


def encode_main(K,order,level,grammar,rckind,startctx):
    zc=zstd.ZstdCompressor(level=level);sh,rc,startg,lens,rcomp,vals,phase,event_first,diag=gather_universal(K,order);nr=lens.size;ne=vals.size
    # Run-count representation.
    if rckind==0:f0=zc.compress(rc.astype('<u2',copy=False).tobytes())
    else:f0=zc.compress(leb_u(rc))
    # Length grammar. Empty unused slots cost zero bytes in the container.
    aux=[b'',b'',b'']
    if grammar==0:aux[0]=zc.compress(leb_u(lens))
    elif grammar==1:
        long=lens>1;aux[0]=zc.compress(np.packbits(long,bitorder='little').tobytes());aux[1]=zc.compress(leb_u(lens[long]-2)) if long.any() else b''
    elif grammar==2:
        long=lens>1;very=lens[long]>2;aux[0]=zc.compress(np.packbits(long,bitorder='little').tobytes());aux[1]=zc.compress(np.packbits(very,bitorder='little').tobytes()) if long.any() else b'';aux[2]=zc.compress(leb_u(lens[long][very]-3)) if very.any() else b''
    else:raise ValueError(grammar)
    sctx=start_context(rcomp,lens,startctx);sgsort,_=reorder_vals(startg,sctx);f1=zc.compress(leb_u(sgsort))
    # Freeze PR #154's winning zero-map run-phase value context.
    signs=vals<0;firstsign=signs[event_first];rep_mask=~event_first;prev=np.empty(ne,bool);k=0
    counts=np.zeros(rc.size,np.int32);j=0
    for i,nr0 in enumerate(rc.tolist()):
        n=int(nr0);c=int(lens[j:j+n].sum()) if n else 0;counts[i]=c;j+=n
        if c:
            prev[k]=signs[k]
            if c>1:prev[k+1:k+c]=signs[k:k+c-1]
            k+=c
    repeat=(signs==prev)[rep_mask];rsort,_=reorder_bits(repeat,phase[rep_mask])
    ab=np.abs(vals);exc=ab!=1;esort,_=reorder_bits(exc,phase);mag=(ab[exc]-2).astype(np.int32);msort,_=reorder_vals(mag,phase[exc]);dc=dtype_code(msort)
    vf=[zc.compress(np.packbits(firstsign,bitorder='little').tobytes()),zc.compress(np.packbits(rsort,bitorder='little').tobytes()),zc.compress(np.packbits(esort,bitorder='little').tobytes()),zc.compress(msort.astype(DT[dc],copy=False).tobytes()) if msort.size else b'']
    frames=[f0,f1,*aux,*vf];oc=int(order[0]|(order[1]<<2)|(order[2]<<4));h=struct.pack(UHDR,UMAG,1,oc,dc,grammar,rckind,startctx,*K.shape,*[len(x) for x in frames])
    parts={'run_counts':len(f0),'run_start_gaps':len(f1),'length_a':len(aux[0]),'length_b':len(aux[1]),'length_c':len(aux[2]),'sign_first':len(vf[0]),'sign_repeat':len(vf[1]),'exception_support':len(vf[2]),'exception_magnitude':len(vf[3]),'timing_bytes':sum(len(x) for x in frames[:5]),'value_bytes':sum(len(x) for x in frames[5:]),'grammar':grammar,'run_count_kind':rckind,'start_context':startctx,'level':level,**diag}
    return h+b''.join(frames),parts


def decode_main(blob):
    q=struct.unpack(UHDR,blob[:UHS]);magic,ver,oc,dc,grammar,rckind,startctx,C,L,S,T,*lensf=q
    if magic!=UMAG or ver!=1:raise RuntimeError('universal header')
    p=UHS;fs=[]
    for n in lensf:fs.append(blob[p:p+n]);p+=n
    if p!=len(blob):raise RuntimeError('universal stream length')
    order=tuple((oc>>(2*i))&3 for i in range(3));shape=(C,L,S,T);psh=tuple(shape[i] for i in order)+(T,);ntr=int(np.prod(psh[:-1]));zd=zstd.ZstdDecompressor()
    rc=np.frombuffer(zd.decompress(fs[0]),'<u2',count=ntr).astype(np.int32) if rckind==0 else leb_dec(zd.decompress(fs[0]),ntr);nr=int(rc.sum());runlens=decode_lengths(grammar,fs,nr,zd)
    rcomp=run_components(rc,order,psh);sctx=start_context(rcomp,runlens,startctx);sgsort=leb_dec(zd.decompress(fs[1]),nr);startg=restore_vals(sgsort,sctx).astype(np.int32);rows=reconstruct_positions(rc,startg,runlens,T);counts,phase,event_first=metadata_from_positions(rows);ne=int(counts.sum());nn=int(np.count_nonzero(counts))
    firstsign=np.unpackbits(np.frombuffer(zd.decompress(fs[5]),np.uint8),bitorder='little',count=nn).astype(bool);rep_mask=~event_first;rsort=np.unpackbits(np.frombuffer(zd.decompress(fs[6]),np.uint8),bitorder='little',count=ne-nn).astype(bool);repeat=restore_bits(rsort,phase[rep_mask]);signs=np.empty(ne,bool);k=fk=rk=0
    for c0 in counts.tolist():
        c=int(c0)
        if not c:continue
        s=bool(firstsign[fk]);fk+=1;signs[k]=s;k+=1
        for _ in range(1,c):
            if not repeat[rk]:s=not s
            rk+=1;signs[k]=s;k+=1
    if k!=ne or fk!=nn or rk!=repeat.size:raise RuntimeError('universal sign accounting')
    esort=np.unpackbits(np.frombuffer(zd.decompress(fs[7]),np.uint8),bitorder='little',count=ne).astype(bool);exc=restore_bits(esort,phase);nex=int(exc.sum());msort=np.frombuffer(zd.decompress(fs[8]),dtype=DT[dc],count=nex).astype(np.int32) if nex else np.empty(0,np.int32);mag=restore_vals(msort,phase[exc]) if nex else msort;ab=np.ones(ne,np.int32);ab[exc]=mag+2;vals=np.where(signs,-ab,ab);tr=np.zeros((ntr,T),np.int32);k=0
    for i,pos in enumerate(rows):
        c=pos.size
        if c:tr[i,pos]=vals[k:k+c];k+=c
    if k!=ne:raise RuntimeError('universal value accounting')
    P=tr.reshape(psh);inv=np.argsort(order);return np.transpose(P,tuple(inv)+(3,))


def decode_out_best(bo,Oshape):
    if bo[1]=='gap':
        R=decode(bo[6]).reshape(Oshape);return undelta(R,1) if bo[2] else R
    R=decode_out_sparse(bo[6]);return undelta(R,1) if bo[2] else R


def main(path):
    order=(0,1,2);level=22
    X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());eps=.1*std;step=2*eps;raw=X.nbytes;G,tm,outids,geom=geometry_map(X,gx,gy)
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    O=np.rint(X[outids]/step).astype(np.int32);K=delta(G,3);rows=[]
    for grammar in (0,1,2):
      for rckind in (0,1):
       for startctx in (0,1,2,3):
        b,parts=encode_main(K,order,level,grammar,rckind,startctx);R=decode_main(b)
        if not np.array_equal(R,K):raise RuntimeError(('main exact decode',grammar,rckind,startctx))
        rows.append({'main_bytes':len(b),'grammar':grammar,'run_count_kind':rckind,'start_context':startctx,'parts':parts,'blob':b})
    rows.sort(key=lambda r:r['main_bytes']);best=rows[0];bo=best_out(O);RO=decode_out_best(bo,O.shape)
    if not np.array_equal(RO,O):raise RuntimeError('outlier exact decode')
    RG=undelta(decode_main(best['blob']),3);recon=np.empty_like(X)
    for tid,c,l,s in tm:recon[tid]=RG[c,l,s].astype(np.float32)*np.float32(step)
    recon[outids]=RO.astype(np.float32)*np.float32(step);me=float(np.max(np.abs(X-recon)));szb,sze=sz3_bytes(X,eps);container=TOPS+best['main_bytes']+int(bo[0]);ratio=raw/container;baseline=133225;gate=baseline/2
    out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'eps':eps,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'main_best':{k:v for k,v in best.items() if k!='blob'},'main_candidates':[{k:v for k,v in r.items() if k!='blob'} for r in rows],'outlier_best':{'bytes':int(bo[0]),'kind':bo[1],'tdiff':bool(bo[2]),'mode':int(bo[3]),'level':int(bo[4])},'top_header_bytes':TOPS,'container_bytes':container,'ratio':ratio,'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'sz3':{'bytes':int(szb),'ratio':raw/szb,'maxerr':float(sze)},'gain_vs_direct_sz3':float(szb/container),'strongest_verified_p75_baseline_bytes':baseline,'gain_vs_strongest_verified_p75_baseline':float(baseline/container),'two_x_gate_bytes':gate,'prior_record_bytes':69006,'clears_two_x_gate':bool(container<gate)}
    print(json.dumps({k:out[k] for k in ('container_bytes','ratio','maxerr','valid','gain_vs_direct_sz3','gain_vs_strongest_verified_p75_baseline','two_x_gate_bytes','clears_two_x_gate')},indent=2),flush=True);json.dump(out,open('soda_universal_run_grammar.json','w'),indent=2)

main(sys.argv[1])
