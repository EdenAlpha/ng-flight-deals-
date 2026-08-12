import json,os,struct,sys
import numpy as np
import zstandard as zstd

# Reuse the audited Soda loader, geometry, outlier codec, timing helpers and
# PR #154 zero-map run-phase value machinery. This experiment changes only
# the main-grid support timing representation.
src=open('research/soda_run_aware_values.py').read().split('\ndef main(path):')[0]
exec(compile(src,'soda_run_aware_values.py','exec'),globals())

HMAG=b'HBMPv001'
HHDR='<8sBBBB4I11Q'
HHS=struct.calcsize(HHDR)
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
    if p!=len(buf):raise RuntimeError(('LEB128 trailing',p,len(buf)))
    return out


def gather_hybrid(K,order,run_threshold,bitmap_min):
    P=np.transpose(K,order+(3,));sh=P.shape;tr=P.reshape(-1,sh[-1]);ntr=tr.shape[0];T=sh[-1]
    counts=np.count_nonzero(tr,axis=1).astype(np.uint16);modes=np.zeros(ntr,np.uint8)
    rawg=[];run_counts=[];startg=[];runlen=[];bitrows=[];vals=[];phases=[];first=[]
    gap_events=run_events=bitmap_events=0;gap_tr=run_tr=bitmap_tr=0;adj=0
    for i,row in enumerate(tr):
        pos=np.flatnonzero(row);c=pos.size
        if not c:continue
        starts,ll=trace_runs(pos);nr=starts.size;adj+=c-nr
        # Mode 2: fixed-width support bitmap for dense traces. Mode 1: exact
        # contiguous-run grammar. Mode 0: ordinary chronological event gaps.
        if c>=bitmap_min:
            mode=2
        elif c>=2 and nr/c<=run_threshold:
            mode=1
        else:
            mode=0
        modes[i]=mode
        if mode==0:
            gap_tr+=1;gap_events+=c;g=np.empty(c,np.int32);g[0]=pos[0]+1
            if c>1:g[1:]=np.diff(pos)
            rawg.extend(g.tolist())
        elif mode==1:
            run_tr+=1;run_events+=c;run_counts.append(nr);prev=-1
            for st,ln in zip(starts.tolist(),ll.tolist()):
                startg.append(int(st)-prev);runlen.append(int(ln));prev=int(st)+int(ln)-1
        else:
            bitmap_tr+=1;bitmap_events+=c;bitrows.append(np.packbits(row!=0,bitorder='little').tobytes())
        vals.extend(row[pos].astype(np.int32).tolist());phases.extend(phase_labels(pos).tolist())
        fm=np.zeros(c,bool);fm[0]=True;first.extend(fm.tolist())
    vals=np.asarray(vals,np.int32);phases=np.asarray(phases,np.uint8);first=np.asarray(first,bool)
    if vals.size!=int(counts.sum()) or phases.size!=vals.size or first.size!=vals.size:raise RuntimeError('hybrid gather accounting')
    diag={'events':int(vals.size),'adjacent_events':int(adj),'adjacent_fraction':float(adj/max(1,vals.size)),'gap_traces':gap_tr,'run_traces':run_tr,'bitmap_traces':bitmap_tr,'gap_events':gap_events,'run_events':run_events,'bitmap_events':bitmap_events,'bitmap_min':int(bitmap_min),'run_threshold':float(run_threshold)}
    return sh,counts,modes,np.asarray(rawg,np.int32),np.asarray(run_counts,np.uint16),np.asarray(startg,np.int32),np.asarray(runlen,np.int32),b''.join(bitrows),vals,phases,first,diag


def reconstruct_positions(counts,modes,rawg,rc,startg,runlen,bitmap_raw,T):
    rows=[];kg=kr=ks=kb=0;rowbytes=(T+7)//8
    for c0,m0 in zip(counts.tolist(),modes.tolist()):
        c=int(c0);m=int(m0)
        if not c:
            rows.append(np.empty(0,np.int32));continue
        if m==0:
            g=rawg[kg:kg+c];kg+=c;pos=(np.cumsum(g)-1).astype(np.int32)
        elif m==1:
            nr=int(rc[kr]);kr+=1;pos=[];prev=-1
            for _ in range(nr):
                st=prev+int(startg[ks]);ln=int(runlen[ks]);ks+=1
                if ln<=0:raise RuntimeError('bad run len')
                pos.extend(range(st,st+ln));prev=st+ln-1
            pos=np.asarray(pos,np.int32)
            if pos.size!=c:raise RuntimeError(('run count',pos.size,c))
        elif m==2:
            b=bitmap_raw[kb:kb+rowbytes];kb+=rowbytes
            if len(b)!=rowbytes:raise RuntimeError('short bitmap row')
            bits=np.unpackbits(np.frombuffer(b,np.uint8),bitorder='little',count=T)
            pos=np.flatnonzero(bits).astype(np.int32)
            if pos.size!=c:raise RuntimeError(('bitmap count',pos.size,c))
        else:raise RuntimeError('bad timing mode')
        if pos.size and (pos[0]<0 or pos[-1]>=T or np.any(np.diff(pos)<=0)):raise RuntimeError('bad positions')
        rows.append(pos)
    if kg!=rawg.size or kr!=rc.size or ks!=runlen.size or kb!=len(bitmap_raw):raise RuntimeError(('timing accounting',kg,rawg.size,kr,rc.size,ks,runlen.size,kb,len(bitmap_raw)))
    return rows


def phase_first_from_rows(rows):
    phase=[];first=[]
    for pos in rows:
        c=pos.size
        if not c:continue
        phase.extend(phase_labels(pos).tolist());fm=np.zeros(c,bool);fm[0]=True;first.extend(fm.tolist())
    return np.asarray(phase,np.uint8),np.asarray(first,bool)


def encode_main(K,order,level,run_threshold,bitmap_min):
    zc=zstd.ZstdCompressor(level=level)
    sh,counts,modes,rawg,rc,startg,runlen,bitmap_raw,vals,phase,event_first,diag=gather_hybrid(K,order,run_threshold,bitmap_min);ne=vals.size
    tf=[zc.compress(counts.astype('<u2',copy=False).tobytes()),zc.compress(np.packbits(modes[:,None]>>np.array([0,1],dtype=np.uint8)&1,axis=None,bitorder='little').tobytes()),zc.compress(leb_u(rawg)),zc.compress(rc.astype('<u2',copy=False).tobytes()),zc.compress(leb_u(startg)),zc.compress(leb_u(runlen)),zc.compress(bitmap_raw)]
    # Freeze PR #154's winning run-phase value context exactly.
    signs=vals<0;firstsign=signs[event_first];rep_mask=~event_first;prev=np.empty(ne,bool);k=0
    for c0 in counts.tolist():
        c=int(c0)
        if not c:continue
        prev[k]=signs[k]
        if c>1:prev[k+1:k+c]=signs[k:k+c-1]
        k+=c
    repeat=(signs==prev)[rep_mask];rsort,_=reorder_bits(repeat,phase[rep_mask])
    ab=np.abs(vals);exc=ab!=1;esort,_=reorder_bits(exc,phase);mag=(ab[exc]-2).astype(np.int32);msort,_=reorder_vals(mag,phase[exc]);dc=dtype_code(msort)
    vf=[zc.compress(np.packbits(firstsign,bitorder='little').tobytes()),zc.compress(np.packbits(rsort,bitorder='little').tobytes()),zc.compress(np.packbits(esort,bitorder='little').tobytes()),zc.compress(msort.astype(DT[dc],copy=False).tobytes()) if msort.size else zc.compress(b'')]
    frames=tf+vf;oc=int(order[0]|(order[1]<<2)|(order[2]<<4));h=struct.pack(HHDR,HMAG,1,oc,dc,0,*K.shape,*[len(x) for x in frames])
    parts={'counts':len(tf[0]),'modes':len(tf[1]),'raw_gaps':len(tf[2]),'run_counts':len(tf[3]),'run_start_gaps':len(tf[4]),'run_lengths':len(tf[5]),'bitmap_support':len(tf[6]),'sign_first':len(vf[0]),'sign_repeat':len(vf[1]),'exception_support':len(vf[2]),'exception_magnitude':len(vf[3]),'timing_bytes':sum(map(len,tf)),'value_bytes':sum(map(len,vf)),'level':level,'order':list(order),**diag}
    return h+b''.join(frames),parts


def decode_main(blob):
    q=struct.unpack(HHDR,blob[:HHS]);magic,ver,oc,dc,_r,C,L,S,T,*lens=q
    if magic!=HMAG or ver!=1:raise RuntimeError('hybrid header')
    p=HHS;fs=[]
    for n in lens:fs.append(blob[p:p+n]);p+=n
    if p!=len(blob):raise RuntimeError('hybrid stream length')
    order=tuple((oc>>(2*i))&3 for i in range(3));shape=(C,L,S,T);psh=tuple(shape[i] for i in order)+(T,);ntr=int(np.prod(psh[:-1]));zd=zstd.ZstdDecompressor()
    counts=np.frombuffer(zd.decompress(fs[0]),'<u2',count=ntr).astype(np.int32)
    modebits=np.unpackbits(np.frombuffer(zd.decompress(fs[1]),np.uint8),bitorder='little',count=2*ntr).reshape(ntr,2);modes=(modebits[:,0]+2*modebits[:,1]).astype(np.uint8)
    ng=int(counts[modes==0].sum());rawg=leb_dec(zd.decompress(fs[2]),ng);nrun=int(np.sum(modes==1));rc=np.frombuffer(zd.decompress(fs[3]),'<u2',count=nrun).astype(np.int32);nr=int(rc.sum());startg=leb_dec(zd.decompress(fs[4]),nr);runlen=leb_dec(zd.decompress(fs[5]),nr);bitmap_raw=zd.decompress(fs[6]);rows=reconstruct_positions(counts,modes,rawg,rc,startg,runlen,bitmap_raw,T)
    phase,event_first=phase_first_from_rows(rows);ne=int(counts.sum());nn=int(np.count_nonzero(counts));firstsign=np.unpackbits(np.frombuffer(zd.decompress(fs[7]),np.uint8),bitorder='little',count=nn).astype(bool);rep_mask=~event_first;rsort=np.unpackbits(np.frombuffer(zd.decompress(fs[8]),np.uint8),bitorder='little',count=ne-nn).astype(bool);repeat=restore_bits(rsort,phase[rep_mask]);signs=np.empty(ne,bool);k=fk=rk=0
    for c0 in counts.tolist():
        c=int(c0)
        if not c:continue
        s=bool(firstsign[fk]);fk+=1;signs[k]=s;k+=1
        for _ in range(1,c):
            if not repeat[rk]:s=not s
            rk+=1;signs[k]=s;k+=1
    if k!=ne or fk!=nn or rk!=repeat.size:raise RuntimeError('sign accounting')
    esort=np.unpackbits(np.frombuffer(zd.decompress(fs[9]),np.uint8),bitorder='little',count=ne).astype(bool);exc=restore_bits(esort,phase);nex=int(exc.sum());msort=np.frombuffer(zd.decompress(fs[10]),dtype=DT[dc],count=nex).astype(np.int32) if nex else np.empty(0,np.int32);mag=restore_vals(msort,phase[exc]) if nex else msort;ab=np.ones(ne,np.int32);ab[exc]=mag+2;vals=np.where(signs,-ab,ab)
    tr=np.zeros((ntr,T),np.int32);k=0
    for i,pos in enumerate(rows):
        c=pos.size
        if c:tr[i,pos]=vals[k:k+c];k+=c
    if k!=ne:raise RuntimeError('value accounting')
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
    # Explicit mode bits make the search dictionary encoder-only. These
    # precommitted thresholds span sparse to very dense bitmap activation.
    for rt in (.4,.5,.6,.7):
      for bm in (64,96,128,192,256,384,512):
        b,parts=encode_main(K,order,level,rt,bm);R=decode_main(b)
        if not np.array_equal(R,K):raise RuntimeError(('main exact decode',rt,bm))
        rows.append({'main_bytes':len(b),'run_threshold':rt,'bitmap_min':bm,'parts':parts,'blob':b})
    rows.sort(key=lambda r:r['main_bytes']);best=rows[0];bo=best_out(O);RO=decode_out_best(bo,O.shape)
    if not np.array_equal(RO,O):raise RuntimeError('outlier exact decode')
    RG=undelta(decode_main(best['blob']),3);recon=np.empty_like(X)
    for tid,c,l,s in tm:recon[tid]=RG[c,l,s].astype(np.float32)*np.float32(step)
    recon[outids]=RO.astype(np.float32)*np.float32(step);me=float(np.max(np.abs(X-recon)));szb,sze=sz3_bytes(X,eps);container=TOPS+best['main_bytes']+int(bo[0]);ratio=raw/container;baseline=133225;gate=baseline/2
    out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'eps':eps,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'main_best':{k:v for k,v in best.items() if k!='blob'},'main_candidates':[{k:v for k,v in r.items() if k!='blob'} for r in rows],'outlier_best':{'bytes':int(bo[0]),'kind':bo[1],'tdiff':bool(bo[2]),'mode':int(bo[3]),'level':int(bo[4])},'top_header_bytes':TOPS,'container_bytes':container,'ratio':ratio,'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'sz3':{'bytes':int(szb),'ratio':raw/szb,'maxerr':float(sze)},'gain_vs_direct_sz3':float(szb/container),'strongest_verified_p75_baseline_bytes':baseline,'gain_vs_strongest_verified_p75_baseline':float(baseline/container),'strict_2x_gate_bytes':gate,'bytes_below_gate':float(gate-container),'previous_pr154_bytes':69006,'previous_pr155_bytes':68646,'improvement_vs_pr155_bytes':int(68646-container)}
    print(json.dumps({k:out[k] for k in ['container_bytes','ratio','gain_vs_direct_sz3','gain_vs_strongest_verified_p75_baseline','strict_2x_gate_bytes','bytes_below_gate','improvement_vs_pr155_bytes','valid','maxerr']},indent=2),flush=True);print(json.dumps(out['main_best'],indent=2),flush=True);json.dump(out,open('soda_hybrid_bitmap_timing.json','w'),indent=2)

main(sys.argv[1])
