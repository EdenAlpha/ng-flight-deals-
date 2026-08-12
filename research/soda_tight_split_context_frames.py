import json,os,struct,sys
import numpy as np

# Reuse PR #176's audited structural semantics, geometry, outlier dictionary,
# Rice incumbent and lossless backend menu.  This experiment changes only the
# framing of already decoder-known inter-run/magnitude contexts.
src=open('research/soda_tight_rice_frames.py').read().split('\ndef main(path,frac):')[0]
exec(compile(src,'soda_tight_rice_frames.py','exec'),globals())

SC_MAGIC=b'SPLCTX01'
SC_PREFIX='<8sBBBB4I'
SC_PHS=struct.calcsize(SC_PREFIX)
ORDER=(0,1,2);CTXMODE=4


def best_frame(raw):
    best,allrows=best_comp(raw);n,m,b=best
    return b,m,{'raw_bytes':len(raw),'chosen':METHOD_NAMES[m],'bytes':n,'all':allrows}


def make_split_raws(K,split_inter,split_mag):
    cache=structural_sequences(K)
    sh,dc,rawframes,meta,rc,lens,rcomp,vals,phase,event_first,ictx,mctx,r2,r9,d2,d9=cache
    # Frame order is self-described by flags, with no context-map bytes:
    # rc, first; inter(1 or 16); long, very, longres, signfirst, signrepeat,
    # exception-support; magnitude(1 or 4).
    raws=[rawframes[0],rawframes[1]];labels=['run_counts','first_starts']
    rf=run_first_mask(rc);inter=(gather_universal(K,ORDER)[2][~rf]-2).astype(np.int32)
    # Audit exact current inter semantics.
    si,_=reorder_vals(inter,ictx)
    if leb_u(si)!=rawframes[2]:raise RuntimeError('split inter audit')
    if split_inter:
        for c in range(16):
            raws.append(leb_u(inter[ictx==c]));labels.append(f'inter_ctx_{c}')
    else:
        raws.append(rawframes[2]);labels.append('inter_starts')
    for i,name in zip((3,4,5,6,7,8),('long_support','very_support','long_residual','sign_first','sign_repeat','exception_support')):
        raws.append(rawframes[i]);labels.append(name)
    ab=np.abs(vals);exc=ab!=1;mag=(ab[exc]-2).astype(np.int32)
    sm,_=reorder_vals(mag,mctx)
    if sm.astype(DT[dc],copy=False).tobytes()!=rawframes[9]:raise RuntimeError('split magnitude audit')
    if split_mag:
        for c in range(4):
            raws.append(np.ascontiguousarray(mag[mctx==c].astype(DT[dc],copy=False)).tobytes());labels.append(f'magnitude_phase_{c}')
    else:
        raws.append(rawframes[9]);labels.append('exception_magnitude')
    return sh,dc,raws,labels,cache


def encode_split(K,split_inter,split_mag):
    sh,dc,raws,labels,cache=make_split_raws(K,split_inter,split_mag);frames=[];methods=[];choices=[]
    for i,(raw,label) in enumerate(zip(raws,labels)):
        b,m,d=best_frame(raw);frames.append(b);methods.append(m);d.update({'frame':i,'label':label});choices.append(d)
    flags=int(split_inter)|(int(split_mag)<<1);oc=int(ORDER[0]|(ORDER[1]<<2)|(ORDER[2]<<4));nf=len(frames)
    h=struct.pack(SC_PREFIX,SC_MAGIC,1,oc,dc,flags,*K.shape)+struct.pack('<B',nf)+bytes(methods)+b''.join(struct.pack('<I',len(x)) for x in frames)
    timing_labels={'run_counts','first_starts','long_support','very_support','long_residual'}
    timing_bytes=0;value_bytes=0
    for f,label in zip(frames,labels):
        if label.startswith('inter_') or label in timing_labels:timing_bytes+=len(f)
        else:value_bytes+=len(f)
    parts={'header_bytes':len(h),'frame_count':nf,'split_inter':bool(split_inter),'split_magnitude':bool(split_mag),'timing_bytes':timing_bytes,'value_bytes':value_bytes,'backend_choices':choices,'labels':labels}
    return h+b''.join(frames),parts


def parse_split(blob):
    if len(blob)<SC_PHS+1:raise RuntimeError('short split main')
    magic,ver,oc,dc,flags,C,L,S,T=struct.unpack(SC_PREFIX,blob[:SC_PHS]);p=SC_PHS
    if magic!=SC_MAGIC or ver!=1:raise RuntimeError('split main header')
    nf=blob[p];p+=1
    if len(blob)<p+nf+4*nf:raise RuntimeError('short split directory')
    methods=list(blob[p:p+nf]);p+=nf;lens=list(struct.unpack('<'+'I'*nf,blob[p:p+4*nf]));p+=4*nf;frames=[]
    for n in lens:frames.append(blob[p:p+n]);p+=n
    if p!=len(blob):raise RuntimeError(('split trailing',p,len(blob)))
    raws=[decomp_one(frames[i],methods[i]) for i in range(nf)]
    return (oc,dc,bool(flags&1),bool(flags&2),(C,L,S,T),raws)


def decode_split(blob):
    oc,dc,split_inter,split_mag,shape,raws=parse_split(blob);C,L,S,T=shape;order=tuple((oc>>(2*i))&3 for i in range(3));psh=tuple(shape[i] for i in order)+(T,);ntr=int(np.prod(psh[:-1]));k=0
    raw0=raws[k];k+=1;raw1=raws[k];k+=1
    rc=leb_dec(raw0,ntr);nr=int(rc.sum());rf=run_first_mask(rc);nn=int(np.count_nonzero(rc));firstcomp=first_components(rc,order,psh);firstg=first_restore(raw1,nn,firstcomp,2)
    ninter=16 if split_inter else 1;inter_raws=raws[k:k+ninter];k+=ninter
    raw3,raw4,raw5,raw6,raw7,raw8=raws[k:k+6];k+=6
    nmag=4 if split_mag else 1;mag_raws=raws[k:k+nmag];k+=nmag
    if k!=len(raws):raise RuntimeError('split frame accounting')
    long=np.unpackbits(np.frombuffer(raw3,np.uint8),bitorder='little',count=nr).astype(bool);nl=int(long.sum());very=np.unpackbits(np.frombuffer(raw4,np.uint8),bitorder='little',count=nl).astype(bool) if nl else np.empty(0,bool);res=leb_dec(raw5,int(very.sum())) if very.any() else np.empty(0,np.int32);runlens=np.ones(nr,np.int32);li=np.flatnonzero(long);runlens[li]=2
    if very.any():runlens[li[very]]=res+3
    rcomp=run_components(rc,order,psh);ictx=inter_context(rc,runlens,rcomp,CTXMODE);ni=nr-nn
    if split_inter:
        inter=np.empty(ni,np.int32)
        for c in range(16):
            cnt=int(np.sum(ictx==c));inter[ictx==c]=leb_dec(inter_raws[c],cnt) if cnt else np.empty(0,np.int32)
    else:
        ss=leb_dec(inter_raws[0],ni);inter=restore_vals(ss,ictx).astype(np.int32)
    startg=np.empty(nr,np.int32);startg[rf]=firstg;startg[~rf]=inter+2;rows=reconstruct_positions(rc,startg,runlens,T);counts,phase,event_first=metadata_from_positions(rows);ne=int(counts.sum())
    firstsign=np.unpackbits(np.frombuffer(raw6,np.uint8),bitorder='little',count=nn).astype(bool);rep_mask=~event_first;rsort=np.unpackbits(np.frombuffer(raw7,np.uint8),bitorder='little',count=ne-nn).astype(bool);repeat=restore_bits(rsort,phase[rep_mask]);signs=np.empty(ne,bool);a=fk=rk=0
    for c0 in counts.tolist():
        c=int(c0)
        if not c:continue
        s=bool(firstsign[fk]);fk+=1;signs[a]=s;a+=1
        for _ in range(1,c):
            if not repeat[rk]:s=not s
            rk+=1;signs[a]=s;a+=1
    if a!=ne or fk!=nn or rk!=repeat.size:raise RuntimeError('split sign accounting')
    esort=np.unpackbits(np.frombuffer(raw8,np.uint8),bitorder='little',count=ne).astype(bool);exc=restore_bits(esort,phase);nex=int(exc.sum());mctx=phase[exc].astype(np.int32)
    if split_mag:
        mag=np.empty(nex,np.int32)
        for c in range(4):
            cnt=int(np.sum(mctx==c));mag[mctx==c]=np.frombuffer(mag_raws[c],dtype=DT[dc],count=cnt).astype(np.int32) if cnt else np.empty(0,np.int32)
    else:
        msort=np.frombuffer(mag_raws[0],dtype=DT[dc],count=nex).astype(np.int32) if nex else np.empty(0,np.int32);mag=restore_vals(msort,mctx) if nex else msort
    ab=np.ones(ne,np.int32);ab[exc]=mag+2;vals=np.where(signs,-ab,ab);tr=np.zeros((ntr,T),np.int32);a=0
    for i,pos in enumerate(rows):
        c=pos.size
        if c:tr[i,pos]=vals[a:a+c];a+=c
    if a!=ne:raise RuntimeError('split value accounting')
    P=tr.reshape(psh);inv=np.argsort(order);return np.transpose(P,tuple(inv)+(3,))


def decode_out_blob(blob,bo,Oshape):
    if bo[1]=='gap':
        A=decode(blob).reshape(Oshape);return undelta(A,1) if bo[2] else A
    A=decode_out_sparse(blob);return undelta(A,1) if bo[2] else A


def incumbent(K,O):
    cache=structural_sequences(K);rows=[]
    for r2 in (0,1):
        for r9 in (0,1):
            mb,parts=encode_main_candidate(K,r2,r9,cache);R=decode_main_candidate(mb)
            if not np.array_equal(R,K):raise RuntimeError('incumbent K')
            rows.append((TOP_HS+len(mb),len(mb),r2,r9,parts))
    rows.sort(key=lambda x:x[0]);bo=best_out(O);return rows[0][0]+int(bo[0]),rows[0],bo


def main(path,frac):
    X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());public_eps=float(frac)*std;internal_eps=public_eps*INTERNAL_SAFETY;step=2*internal_eps;raw=int(X.nbytes);G,tm,outids,geom=geometry_map(X,gx,gy)
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    O=np.rint(X[outids]/step).astype(np.int32);K=delta(G,3);inc,incm,bo=incumbent(K,O);RO=decode_out_blob(bo[6],bo,O.shape)
    if not np.array_equal(RO,O):raise RuntimeError('split outlier incumbent')
    rows=[]
    for si,sm in ((True,False),(False,True),(True,True)):
        mb,parts=encode_split(K,si,sm);RK=decode_split(mb)
        if not np.array_equal(RK,K):raise RuntimeError(('split exact K',si,sm))
        total=TOP_HS+len(mb)+int(bo[0]);RG=undelta(RK,3);Y=np.empty_like(X)
        for tid,c,l,s in tm:Y[tid]=RG[c,l,s].astype(np.float32)*np.float32(step)
        Y[outids]=RO.astype(np.float32)*np.float32(step);me=float(np.max(np.abs(X-Y)))
        if me>public_eps*(1+3e-6):raise RuntimeError(('split hard error',si,sm,me,public_eps))
        rows.append({'split_inter':si,'split_magnitude':sm,'main_bytes':len(mb),'container_bytes':total,'ratio':raw/total,'maxerr':me,'valid':True,'parts':parts})
    rows.sort(key=lambda r:r['container_bytes']);best=rows[0];szb,sze=sz3_bytes(X,public_eps)
    out={'file':os.path.basename(path),'shape':list(X.shape),'epsilon_fraction_of_std':float(frac),'public_eps':public_eps,'internal_eps':internal_eps,'raw_bytes':raw,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'incumbent':{'container_bytes':inc,'main_bytes':incm[1],'rep_inter_rice':bool(incm[2]),'rep_magnitude_rice':bool(incm[3]),'parts':incm[4]},'best_split':best,'all_split':rows,'improvement_vs_incumbent':inc/best['container_bytes'],'sz3':{'bytes':int(szb),'ratio':raw/szb,'maxerr':float(sze)},'gain_vs_direct_sz3':szb/best['container_bytes']}
    print(json.dumps({'frac':frac,'incumbent_bytes':inc,'best_split_inter':best['split_inter'],'best_split_magnitude':best['split_magnitude'],'best_bytes':best['container_bytes'],'improvement':out['improvement_vs_incumbent'],'gain_sz3':out['gain_vs_direct_sz3'],'header_bytes':best['parts']['header_bytes'],'timing_bytes':best['parts']['timing_bytes'],'value_bytes':best['parts']['value_bytes']},indent=2),flush=True);json.dump(out,open('soda_tight_split_context_frames.json','w'),indent=2)

main(sys.argv[1],float(sys.argv[2]))
